# Intel Arc与NPU：Vulkan、SYCL、IR和语音任务完整对照

[工程实例索引](README.md) · [知识体系总目录](../SUMMARY.md)

技术标签：`Core Ultra 7 256V / 16GB / OpenVINO / ASR / TTS`

## 环境与三条执行路径

| 项目 | 已记录条件 |
| --- | --- |
| 设备 | Core Ultra7 256V，Arc Lunar Lake GPU，NPU，16GB共享内存 |
| 系统 / 工具 | Ubuntu24.04.4、Mesa26.1.4、oneAPI2026.1.0、OpenVINO2026.2.1 |
| GGUF | llama.cpp Vulkan与SYCL；GPU23层/CPU10层，pp512/tg128三轮 |
| IR | Qwen3.5-9B INT4/INT8固定revision与文件清单 |
| 语音 | Whisper ASR、BabelVox混合TTS、全NPU实验、Qwen3-TTS与Kokoro48例 |

## 部署适配执行顺序

```text
驱动与设备枚举 → 独立Vulkan/SYCL构建 → 同GGUF分层与pp/tg
 → IR文件校验 → GenAI GPU管线 → 功能完整性
 → NPU编译和shape检查 → 语音分模块 → 完整音频质量 → RTF与RSS
```

GPU、NPU是不同执行目标，不能只把device字符串改掉就沿用GPU成功结论。NPU编译失败、超时、fallback、错误音频和CPU成功分别记录。Windows IPEX-LLM/Ollama属于另一版本组合，下方保留原操作而不混入Linux基线。

## 实际优化与结果

| 实验 | 观测 | 工程判断 |
| --- | --- | --- |
| IR INT4/INT8 GPU | 固定输入的生成速率观察比值约2.09 | 输出处于思考截断阶段，质量未完成 |
| Vulkan/SYCL | 同pp/tg与23/10层对比 | 引擎时间不与HTTP直接排名 |
| Whisper NPU | 4.4s音频，三轮核心时间约0.17s | 进程冷启动另记，核心RTF约0.039 |
| BabelVox全NPU | 性能达标，音频内容错误 | 质量失败，回滚混合路径 |
| Kokoro CPU | 48例、P95 RTF0.189、约3GiB RSS | 实时目标通过，原内存目标失败 |
| Kokoro NPUW | 首次超过20分钟，缓存复测120s超时 | 无WAV，不能报告NPU吞吐 |

验收分四项：功能完整、内容正确、实时性、内存预算。全NPU和最低RTF不是最终目标；失败方案保留输入shape、编译配置和退出状态，便于下一版回归。原17节报告、三轮数据、所有后续TTS实验与Windows路线完整保留如下。

## 完整技术记录的使用约定

以下直接保留相关FlowUs文章的技术正文、命令、表格、日志、失败和后续实验，不以摘要替代原过程。私人路径、节点、认证与附件地址脱敏；`<NODE_IP>`等占位符需要按当前环境填写。原建议或预测仍是建议或预测。上方执行顺序与技术修订用于解释历史记录中的冲突，历史GPU/NPU实验未在本轮重跑。

## R35 · Qwen3.5-9B Intel openvino 平台推理对比报告

> 测试日期：2026-07-15
> 设备：Intel Core Ultra 7 256V，Intel Arc Graphics (Lunar Lake)，Intel NPU，16 GB 统一内存
> 系统：Ubuntu 24.04.4 LTS，Linux 6.17.0-14-generic

#### 1. 结论

1. **OpenVINO GenAI GPU + 官方 INT4 IR** 是当前性能最好且已实测成功的方案：`21.16 tokens/s`，TTFT `184.02 ms`，超过 `12 tokens/s` 目标。

2. OpenVINO INT8 GPU 推理成功，但只有 `10.10 tokens/s`，INT4 约为 INT8 的 `2.09x`，因此生产优先使用 INT4。

3. llama.cpp Vulkan + Mesa 26.1.4 为当前稳定服务方案，benchmark 为 `11.54 tokens/s`，实际 API 为 `11.38 tokens/s`。

4. llama.cpp SYCL 可用，但生成速度 `10.22 tokens/s`，低于 Mesa 26.1.4 Vulkan。

5. OpenVINO INT4 NPU 在 VPUX compiler 阶段硬失败；INT8 NPU 编译 420 秒仍未完成，已超时终止。当前 NPU 方案不可用于生产。

6. llama.cpp OpenVINO WIP backend 能编译和枚举设备，但无法运行当前 Qwen3.5-9B GGUF；正确的 OpenVINO 路径是官方预转换 IR + OpenVINO GenAI。

#### 2. 硬件与软件环境

| 项目 | 配置 |
| --- | --- |
| CPU | Intel Core Ultra 7 256V |
| GPU | Intel Arc Graphics (LNL), device ID 0x64a0 |
| NPU | Intel NPU，OpenVINO 可枚举 |
| 内存 | 16 GB CPU/GPU/NPU 统一内存 |
| Mesa | 26.1.4~kisak1~n |
| Vulkan API | 1.4.354 |
| Vulkan driver | Intel open-source Mesa driver 26.1.4 |
| oneAPI compiler | 2026.1.0 |
| OpenVINO | 2026.2.1 |
| OpenVINO GenAI | 2026.2.1.0 |
| OpenVINO Tokenizers | 2026.2.1.0 |
| Optimum Intel | 2.0.0 |
| Transformers | 5.0.0 |
| llama.cpp ggml version | 0.16.0，源码快照无 .git，commit unknown |

OpenVINO 可用设备：

```text
CPU,GPU,NPU
```

#### 3. 模型

##### 3.1 llama.cpp GGUF

```text
/srv/llm/models/gguf/qwen3.5-9b/Qwen3.5-9B-Q4_K_M.gguf
```

- 参数量：8.95B

- 文件大小：约 5.23 GiB

- 量化：Q4_K_M

- GPU/CPU 混合：33 个可卸载层中 23 层 GPU、10 层 CPU，CPU 层数占约 30.3%

##### 3.2 OpenVINO INT4 IR

```text
/srv/llm/models/openvino/Qwen3.5-9B-int4-ov
```

- 仓库：`OpenVINO/Qwen3.5-9B-int4-ov`

- revision：`3f31fc1609edb0cbc8b131bc4c291f1b15cb0676`

- 量化：INT4_ASYM，group size 128

- 24 个文件，`6,129,582,094` bytes

- 完整性：总字节数与官方元数据一致，无 `.incomplete`

##### 3.3 OpenVINO INT8 IR

```text
/srv/llm/models/openvino/Qwen3.5-9B-int8-ov
```

- 仓库：`OpenVINO/Qwen3.5-9B-int8-ov`

- revision：`3054198f70b6d50b97fa17ae80314e590c57def0`

- 量化：INT8

- 24 个文件，`9,457,724,353` bytes

- 完整性：总字节数与官方元数据一致，无 `.incomplete`

- language IR 解析：4 inputs、1 output、9,112 ops

#### 4. 总体性能对比

> `llama-bench`、llama.cpp HTTP API 和 OpenVINO GenAI `PerfMetrics` 的计时边界不完全相同。表中保留测试类型，不把不同边界的结果冒充为同一 benchmark。

| 序号 | 路径 | 模型 | 设备/分层 | 测试类型 | Prompt | Generation | 结果 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | llama.cpp Vulkan | Q4_K_M | GPU 23 / CPU 10, Mesa 25.2.8 | llama-bench | 未保留 | 约 7.76 t/s | 成功，旧驱动基线 |
| 2 | llama.cpp SYCL | Q4_K_M | GPU 23 / CPU 10 | llama-bench, pp512/tg128, 3 rounds | 353.70 ± 15.31 t/s | 10.22 ± 0.19 t/s | 成功 |
| 3 | llama.cpp SYCL | Q4_K_M | GPU 23 / CPU 10 | HTTP API, 16/128 tokens | 11.67 t/s | 9.21 t/s | 成功，短请求 |
| 4 | llama.cpp Vulkan | Q4_K_M | GPU 23 / CPU 10, Mesa 26.1.4 | llama-bench, pp512/tg128, 3 rounds | 244.91 ± 0.79 t/s | 11.54 ± 0.13 t/s | 成功 |
| 5 | llama.cpp Vulkan | Q4_K_M | GPU 23 / CPU 10, Mesa 26.1.4 | HTTP API, 22/128 tokens | 10.53 t/s | 11.38 t/s | 成功，当前服务 |
| 6 | OpenVINO GenAI | INT4 IR | GPU | VLMPipeline, 19/128 tokens | 未单独测量 | 21.16 ± 0.71 t/s | 成功，最优 |
| 7 | OpenVINO GenAI | INT8 IR | GPU | VLMPipeline, 19/128 tokens | 未单独测量 | 10.10 ± 0.18 t/s | 成功 |
| 8 | OpenVINO GenAI | INT4 IR | NPU | VLMPipeline compile | — | — | VPUX compiler 失败 |
| 9 | OpenVINO GenAI | INT8 IR | NPU | VLMPipeline compile | — | — | 420 s 超时，未进入生成 |
| 10 | llama.cpp OpenVINO | Q4_K_M | GPU | llama-bench | — | — | cache_r_l0 / CPY 不支持 |

#### 5. OpenVINO GPU 详细指标

两次正式测试使用同一提示词：

```text
请用中文简要说明人工智能推理加速的作用。
```

两者均使用：

```text
max_new_tokens=128
do_sample=False
输入 tokens=19
生成 tokens=128
```

| 指标 | INT4 GPU | INT8 GPU | INT4 相对 INT8 |
| --- | --- | --- | --- |
| Pipeline load | 8.251 s（另一次冷启动 13.528 s） | 12.140 s | INT4 更快 |
| Warmup 8 tokens | 1.265 s（第一次记录） | 1.073 s | 不作为主性能指标 |
| TTFT | 184.02 ms | 169.73 ms | INT8 低 14.29 ms |
| TPOT | 47.26 ms/token | 98.96 ms/token | INT4 约减少 52.2% |
| Throughput | 21.1599 ± 0.7100 t/s | 10.1047 ± 0.1766 t/s | 2.09x |
| Generate duration | 6,193.33 ms | 12,745.07 ms | INT4 约快 2.06x |
| Inference duration | 未保留 | 12,610.92 ms | — |
| Tokenization | 0.518 ms | 2.058 ms | 影响很小 |
| Detokenization | 7.221 ms | 6.776 ms | 影响很小 |

##### 5.1 解读

- INT8 TTFT 比 INT4 低约 14 ms，但这个优势很小，且只有单次样本，不应视为稳定结论。

- 连续生成阶段 INT4 的 TPOT 约为 INT8 的一半，生成吞吐达到 INT8 的 2.09 倍。

- 设备只有 16 GB 统一内存，INT4 模型约 6.13 GB，INT8 约 9.46 GB；INT4 同时具有更低内存压力和更高吞吐。

- 当前性能结果支持将 INT4 GPU 作为 OpenVINO 生产候选，INT8 作为精度对照或兼容性备选，不建议作为默认性能方案。

#### 6. NPU 测试记录

##### 6.1 INT4 NPU

OpenVINO 能够枚举 NPU，但 `VLMPipeline(model, "NPU")` 在 VPUX compiler 阶段失败：

```text
StopLocationVerifierPass Pass failed:
Found 32 duplicated names after full verification

Compilation failed.
vclAllocatedExecutableCreate3 result: 0x78000004
[NPU_VCL] Compiler returned msg: Compilation failed
```

结论：硬失败，未进入 token generation。

##### 6.2 INT8 NPU

- NPU 设备枚举成功。

- `VLMPipeline(model, "NPU")` 编译持续 420 秒无完成输出。

- 由 `timeout 420` 终止，exit code `124`。

- 未进入预热或 token generation，因此不能报告 NPU 推理吞吐。

结论：记为“NPU 编译超时”，不记为推理成功；也不把超时等同于明确 compiler error。

#### 7. llama.cpp OpenVINO 失败记录

llama.cpp `GGML_OPENVINO=ON` 编译成功，并能枚举 OpenVINO backend，但用 Qwen3.5-9B Q4_K_M GGUF 创建推理图时失败：

```text
pre-allocated tensor
(cache_r_l0 (view) (copy of ))
in a buffer (OPENVINO0)
that cannot run the operation (CPY)
```

分别在开启和关闭 `GGML_OPENVINO_STATEFUL_EXECUTION` 时复现。这是 llama.cpp OpenVINO WIP backend 对当前 Qwen3.5 GGUF 图的兼容性问题，不代表 OpenVINO 官方 IR 无法在 GPU 上运行。

#### 8. Mesa 升级效果

| 驱动 | Vulkan generation | 变化 |
| --- | --- | --- |
| Mesa 25.2.8 | 约 7.76 t/s | 基线 |
| Mesa 26.1.4 | 11.54 ± 0.13 t/s | 约 +48.7% |

Mesa 26.1.4 使 Vulkan 从明显慢于 SYCL 提升到稍快于 SYCL：

```text
Vulkan 26.1.4: 11.54 t/s
SYCL:           10.22 t/s
相对提升:       约 12.9%
```

#### 9. 测试命令

##### 9.1 Vulkan benchmark

```text
/srv/llm/src/llama.cpp/build/bin/llama-bench \
  -m /srv/llm/models/gguf/qwen3.5-9b/Qwen3.5-9B-Q4_K_M.gguf \
  -ngl 23 \
  -t 8 \
  -fa on \
  -p 512 \
  -n 128 \
  -r 3
```

##### 9.2 SYCL benchmark

```text
source /opt/intel/oneapi/setvars.sh --force
export ONEAPI_DEVICE_SELECTOR=level_zero:0
export ZES_ENABLE_SYSMAN=1

/srv/llm/src/llama.cpp/build-sycl/bin/llama-bench \
  -m /srv/llm/models/gguf/qwen3.5-9b/Qwen3.5-9B-Q4_K_M.gguf \
  -ngl 23 \
  -t 8 \
  -fa on \
  -p 512 \
  -n 128 \
  -r 3
```

##### 9.3 OpenVINO GenAI GPU

```text
import openvino_genai as ov_genai

model = "/srv/llm/models/openvino/Qwen3.5-9B-int4-ov"
pipe = ov_genai.VLMPipeline(model, "GPU")

# 预热
pipe.generate("Hello", max_new_tokens=8, do_sample=False)

result = pipe.generate(
    "请用中文简要说明人工智能推理加速的作用。",
    max_new_tokens=128,
    do_sample=False,
)

metrics = result.perf_metrics
print(metrics.get_num_input_tokens())
print(metrics.get_num_generated_tokens())
print(metrics.get_ttft().mean)
print(metrics.get_tpot().mean)
print(metrics.get_throughput().mean)
```

INT8 只需将 `model` 替换为：

```text
/srv/llm/models/openvino/Qwen3.5-9B-int8-ov
```

#### 10. 输出行为与限制

- INT4/INT8 OpenVINO 测试均正常生成内容，但 Qwen3.5 默认先生成 reasoning/thinking 文本。

- `max_new_tokens=128` 时输出在 reasoning 阶段达到长度限制，未进入最终中文答案；这不是推理失败。

- 性能比较重点是同样 19 input tokens、128 generated tokens 下的 INT4/INT8 GPU 差异。

- 本报告中的单次 API/GenAI 记录不等于长时间稳定性测试；上线 OpenVINO 服务前还应补充多轮、长上下文、并发和内存压力测试。

#### 11. 生产建议

##### 强推荐

```text
OpenVINO GenAI + Qwen3.5-9B INT4 IR + Intel GPU
```

理由：

- 已完成真实 token generation。

- `21.16 tokens/s` 显著超过 `12 tokens/s` 目标。

- 比 INT8 GPU 快 2.09 倍。

- 比当前 Vulkan benchmark 快约 83.4%。

- 模型更小，更适合 16 GB 统一内存。

##### 回退顺序

1. llama.cpp Vulkan + Mesa 26.1.4：当前稳定服务，11.54 t/s benchmark。

2. llama.cpp SYCL：稳定可用，10.22 t/s。

3. OpenVINO INT8 GPU：功能成功，但当前性能低于 Vulkan benchmark，不作为默认性能选择。

##### 暂不使用

- OpenVINO INT4 NPU：VPUX compiler 明确失败。

- OpenVINO INT8 NPU：420 秒编译超时。

- llama.cpp OpenVINO + Qwen3.5 GGUF：`CPY` 图操作不兼容。

#### 12. 当前运行状态

2026-07-15 进行 ASR/TTS NPU 专项测试前，按用户要求停止 llama.cpp Vulkan LLM 服务以释放统一内存。测试后保持停止，没有自动恢复：

```text
qwen35-9b-gpu.service: inactive
enabled: enabled
```

服务仍保留开机自启配置，但当前未运行，因此以下端口暂时不提供 LLM API：

```text
http://<NODE_IP>:8009/v1
```

重启 LLM 服务的命令为：

```text
sudo systemctl start qwen35-9b-gpu.service
```

#### 13. OpenVINO NPU ASR/TTS 实测

##### 13.1 测试条件

| 项目 | 配置 |
| --- | --- |
| OpenVINO | 2026.2.1 |
| OpenVINO GenAI | 2026.2.1.0 |
| NPU | Intel(R) AI Boost |
| LLM 服务 | 停止，避免统一内存竞争 |
| TTS | BabelVox OpenVINO INT8，Chinese，NPU |
| ASR | Whisper Base OpenVINO INT8，Chinese transcribe，NPU |
| 重复次数 | TTS 3 轮，ASR 3 轮 |
| 进程测量 | /usr/bin/time -v |

ASR 模型：

```text
/srv/llm/models/asr/whisper-base-int8-ov
磁盘占用：83 MiB
```

TTS 模型：

```text
/srv/llm/models/tts/babelvox-openvino-int8
磁盘占用：2.5 GiB
```

TTS OpenVINO compiled model cache：

```text
/srv/llm/cache/openvino/tts
磁盘占用：1.8 GiB
```

##### 13.2 TTS NPU 测试

输入文本：

```text
你好，这是英特尔NPU语音合成性能测试。OpenVINO正在进行本地语音推理。
```

参数：

```text
device=NPU
precision=int8
cp-kv-cache=on
talker buckets=64,128,256
language=Chinese
max_tokens=256
```

BabelVox 明确枚举并使用：

```text
NPU device: Intel(R) AI Boost
Generating with BabelVox (NPU)
```

| 指标 | Run 1 | Run 2 | Run 3 | 三轮均值 | 热缓存均值（Run 2/3） |
| --- | --- | --- | --- | --- | --- |
| OpenVINO models compile | 3.3 s | 1.5 s | 1.5 s | 2.10 s | 1.50 s |
| Weights + tokenizer load | 1.5 s | 0.6 s | 0.6 s | 0.90 s | 0.60 s |
| Codec frames | 42 | 42 | 55 | 46.33 | 48.5 |
| 核心生成耗时 | 5.1 s | 4.7 s | 6.6 s | 5.47 s | 5.65 s |
| 输出音频时长 | 3.36 s | 3.36 s | 4.40 s | 3.71 s | 3.88 s |
| BabelVox 报告 RTF | 1.5 | 1.3 | 1.4 | 1.40 | 1.35 |
| 进程端到端墙钟 | 15.18 s | 11.30 s | 12.61 s | 13.03 s | 11.96 s |
| 峰值 RSS | 4,415,732 KiB | 4,584,960 KiB | 4,585,956 KiB | 4,528,883 KiB | 4,585,458 KiB |
| Swap | 0 | 0 | 0 | 0 | 0 |

解读：

- TTS 三轮均成功，确认在 NPU 上执行 talker、speaker encoder 和 tokenizer decoder。

- `CP prefill+decode` 日志明确显示使用 CPU KV cache，因此这是 NPU + CPU 协同路径，不是所有算子 100% 在 NPU。

- 缓存命中后模型编译从 3.3 s 降到 1.5 s，权重/tokenizer 加载从 1.5 s 降到 0.6 s。

- BabelVox 报告的 RTF 为 `1.3～1.5`，表示核心生成耗时仍高于生成音频时长，尚未达到实时 TTS。

- Run 3 生成 55 codec frames，而前两轮为 42，说明当前生成存在随机性；不应只比较墙钟时间而忽略输出时长差异。

- 峰值 RSS 约 4.21～4.37 GiB，无 swap。

有效输出样例：

```text
/srv/llm/outputs/tts-npu.wav
PCM signed 16-bit, mono, 24000 Hz
```

原始日志：

```text
/srv/llm/outputs/benchmarks/tts/tts-run-1.log
/srv/llm/outputs/benchmarks/tts/tts-run-2.log
/srv/llm/outputs/benchmarks/tts/tts-run-3.log
```

TTS 当前存在两个非致命 warning：

1. `qwen3_tts` model type 与实例化类型的 compatibility warning。

2. tokenizer regex warning，上游建议使用 `fix_mistral_regex=True`。

这两个 warning 没有阻止本次生成，但在语音质量/文本覆盖率验收前不应忽略。

##### 13.3 ASR NPU 测试

输入文件：

```text
/srv/llm/outputs/tts-npu.wav
PCM signed 16-bit, mono, 24000 Hz
音频时长：4.400 s
```

WhisperPipeline 会通过 librosa 将输入重采样为 16 kHz mono，并使用：

```text
ov_genai.WhisperPipeline(
    "/srv/llm/models/asr/whisper-base-int8-ov",
    "NPU",
)
```

识别配置：

```text
language=<|zh|>
task=transcribe
```

三轮输出一致：

```text
你好,这是英特尔NPU語音合成服务
```

| 指标 | Run 1 | Run 2 | Run 3 | 三轮均值 | 热缓存均值（Run 2/3） |
| --- | --- | --- | --- | --- | --- |
| 音频时长 | 4.400 s | 4.400 s | 4.400 s | 4.400 s | 4.400 s |
| 核心 infer | 0.173 s | 0.169 s | 0.172 s | 0.171 s | 0.171 s |
| RTF | 0.039 | 0.038 | 0.039 | 0.0387 | 0.0385 |
| 等效实时倍速 1/RTF | 25.64x | 26.32x | 25.64x | 25.86x | 25.97x |
| 进程端到端墙钟 | 8.97 s | 1.65 s | 1.66 s | 4.09 s | 1.66 s |
| 峰值 RSS | 1,277,992 KiB | 764,444 KiB | 764,588 KiB | 935,675 KiB | 764,516 KiB |
| Swap | 0 | 0 | 0 | 0 | 0 |

解读：

- Whisper Base INT8 在 OpenVINO NPU 上完成三轮实际转写，不再是仅有模型和脚本。

- 核心转写 RTF 约 `0.0387`，即约 25.9 倍实时速度，性能充足。

- 首轮进程墙钟 8.97 s 包含 Python 启动、音频加载/重采样、OpenVINO NPU 编译和 pipeline 初始化；不能用 0.173 s 代替冷启动端到端延迟。

- 缓存命中后新进程端到端时间约 1.65～1.66 s，峰值 RSS 约 746.6 MiB，无 swap。

- 三轮输出完全一致，稳定性良好。

- 输入音频的原文更长，ASR 只识别出“你好，这是英特尔 NPU 语音合成服务”；这主要反映 TTS 实际生成内容/音频终止与输入文本并不完全一致，不能用这一个合成样本计算通用 ASR 准确率。

原始日志：

```text
/srv/llm/outputs/benchmarks/asr/asr-run-1.log
/srv/llm/outputs/benchmarks/asr/asr-run-2.log
/srv/llm/outputs/benchmarks/asr/asr-run-3.log
```

##### 13.4 ASR/TTS 结论

| 任务 | OpenVINO NPU 功能 | 核心性能 | 冷启动/进程端到端 | 峰值内存 | 生产判断 |
| --- | --- | --- | --- | --- | --- |
| ASR Whisper Base INT8 | 通过 | RTF 0.0387，约 25.9x 实时 | 首轮 8.97 s，缓存后新进程 1.66 s | 首轮 1.22 GiB，缓存后 0.73 GiB | 性能可用，需补真实语音集准确率测试 |
| TTS BabelVox INT8 | 通过 | RTF 约 1.40 | 首轮 15.18 s，缓存后 11.96 s | 约 4.21～4.37 GiB | 功能可用，尚未实时，需优化和质量验收 |

ASR 的核心转写性能足够支撑实时场景。TTS 已成功使用 NPU，但当前核心 RTF 大于 1，尚不能边生成边以实时速度播放完整音频。

#### 14. TTS 全 NPU 优化实验

##### 14.1 实验目标与源码现状

目标是将 BabelVox TTS 的 OpenVINO 子图全部放到 NPU，并将 RTF 从基线约 `1.40` 降到 `1.0` 以下。

BabelVox 当前上游实现在 `device=NPU` 时的实际分配为：

| 子图 | 基线设备 |
| --- | --- |
| Speaker encoder | NPU |
| Talker 64/128/256 buckets | NPU |
| Tokenizer decoder | NPU |
| Code Predictor prefill/decode | CPU |
| Code Predictor KV cache | CPU memory |

源码中存在明确硬编码：

```text
self.cp_prefill = core.compile_model(..., "CPU")
self.cp_decode = core.compile_model(..., "CPU")
```

因此仅传入 `--device NPU` 并不是全 NPU。

##### 14.2 实验补丁

实验补丁对 CP 图做固定 shape，并禁用 CPU fallback：

```text
cp_prefill inputs_embeds: [1,2,1024]
cp_decode inputs_embeds: [1,1,1024]
cp_decode attention_mask: [1,1,1,20]
past_keys/past_values: [5,1,8,20,128]
fallback_cpu: false
```

日志确认 CP KV cache 路径成功在 NPU 编译：

```text
NPU device: Intel(R) AI Boost
CP prefill+decode: 1.7s (NPU/NPU - KV cache)
Tok decoder: 96.9s (NPU)
```

同时还测试了不使用 CP KV cache 的完整 Code Predictor NPU 路径，以排除单一 KV cache 实现问题。

##### 14.3 CP KV-cache 全 NPU 性能

使用固定随机种子 `20260715`、`max_tokens=128`、相同中文文本进行三轮。三个 WAV 的 SHA-256 完全相同，说明结果可复现。

| 指标 | Run 1 | Run 2 | Run 3 | 热缓存均值（Run 2/3） |
| --- | --- | --- | --- | --- |
| Pipeline load | 127.03 s | 3.89 s | 2.17 s | 3.03 s |
| 核心生成 | 7.572 s | 7.421 s | 7.381 s | 7.401 s |
| 输出音频 | 10.24 s | 10.24 s | 10.24 s | 10.24 s |
| RTF | 0.739 | 0.725 | 0.721 | 0.723 |
| 进程端到端墙钟 | 138.41 s | 14.94 s | 12.52 s | 13.73 s |
| 峰值 RSS | 5,589,676 KiB | 4,553,232 KiB | 4,550,872 KiB | 4,552,052 KiB |
| Swap | 0 | 0 | 0 | 0 |

从纯速度看，RTF 从基线约 `1.40` 降到 `0.723`，核心生成已快于实时播放。

但三轮均达到 128 codec-frame 上限，未自然生成 EOS。对 Run 3 输出使用 Whisper Base INT8 NPU 回译，只得到：

```text
我
```

原输入为完整的两句中文，回译结果与输入严重不符。因此该路径虽然速度达标，但输出无效，不能部署。

原始日志：

```text
/srv/llm/outputs/benchmarks/tts-all-npu/run-1.log
/srv/llm/outputs/benchmarks/tts-all-npu/run-2.log
/srv/llm/outputs/benchmarks/tts-all-npu/run-3.log
/srv/llm/outputs/benchmarks/tts-all-npu/run-3-asr-qc.log
```

##### 14.4 完整 Code Predictor 全 NPU 复核

关闭 CP KV cache，改用固定 `[1,17,1024]` 的完整 Code Predictor NPU 图：

| 指标 | 结果 |
| --- | --- |
| Pipeline cold load | 125.03 s |
| 核心生成 | 7.497 s |
| 输出音频 | 10.24 s |
| RTF | 0.732 |
| 进程墙钟 | 135.72 s |
| 峰值 RSS | 5,713,012 KiB |
| ASR 回译 | 我 |

完整 CP 与 CP KV cache 两条全 NPU 路径都生成无效音频，说明问题不仅是 KV cache 状态管理，而是当前 INT8 Code Predictor IR 在 NPU 上的数值精度、固定 shape 语义或 NPU 算子兼容性问题。

##### 14.5 最终判定与回滚

| 路径 | 设备分配 | RTF | 语音正确性 | 可部署 |
| --- | --- | --- | --- | --- |
| 上游基线 | Talker/Speaker/Decoder=NPU，CP=CPU | 约 1.40 | 可识别中文 | 可，但非实时 |
| 全 NPU CP KV cache | 全部 OpenVINO 子图=NPU | 0.723 | 失败，回译仅“我” | 不可 |
| 全 NPU 完整 CP | 全部 OpenVINO 子图=NPU | 0.732 | 失败，回译仅“我” | 不可 |

结论：

> 当前 BabelVox INT8 模型可以将全部 OpenVINO 子图编译到 Intel NPU，且速度达到实时；但 Code Predictor NPU 输出不正确，最终音频不可用。因此当前不能同时满足“全 NPU”、“实时”和“输出正确”三项要求。

为避免将错误音频路径用于生产，远程 Python 环境已恢复上游原始 `pipeline.py`：

```text
SHA-256: 5e5151bc3852b9cf0ea22585d34ad8fe8ae52932ee747b5764b3eb4f0af4ca84
hybrid_pipeline_restored=true
```

全 NPU 实验补丁与基准脚本保留在项目中，用于向 BabelVox/OpenVINO/NPU 上游提交可复现问题，不用于当前生产运行。

#### 15. Qwen3-TTS 0.6B 官方 OpenVINO Pipeline 实测

##### 15.1 模型与环境

为区分 BabelVox 定制导出路线，本次下载并测试了按 OpenVINO 官方 Notebook 模型结构转换的社区成品：

```text
Repository: aurora2035/Qwen3-TTS-12Hz-0.6B-CustomVoice-OpenVINO-INT8
Remote path: /srv/llm/models/tts/Qwen3-TTS-12Hz-0.6B-CustomVoice-OpenVINO-INT8
Download size: about 1.55 GiB
Source model: Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice
```

模型包含 Talker Language Model、Code Predictor、Text/Codec Embedding、Text Projection 以及 Speech Tokenizer Encoder/Decoder 的 OpenVINO IR。

独立环境：

```text
/srv/llm/venvs/qwen3-tts-ov
OpenVINO 2026.2.1
torch 2.8.0+cpu
torchaudio 2.8.0+cpu
transformers 4.57.3
qwen-tts 0.1.1
```

OpenVINO 官方 Qwen3-TTS Notebook 当前的设备控件显式使用 `exclude=["NPU"]`，因此官方示例并未声明该转换结构可直接在 NPU 上运行。

##### 15.2 OpenVINO CPU 加载与推理

使用 `vivian` 预置音色、中文测试文本和 `max_new_tokens=128`：

| 指标 | 实测值 |
| --- | --- |
| Pipeline load | 2.704 s |
| 核心生成 | 8.735 s |
| 输出音频 | 8.000 s |
| RTF | 1.092 |
| 采样率 | 24,000 Hz |
| 峰值 RSS | 3,777,252 KiB（约 3.60 GiB） |
| Swap | 0 |

输出 WAV：

```text
/srv/llm/outputs/benchmarks/qwen3-tts-official/cpu.wav
SHA-256: e7fc70a7f8161c688b7f4084c6941e505a92f26ab430cdf0eb58cd6cd76ee161
```

使用 Whisper Base INT8 NPU 回译：

```text
你好,這是Q準TTS在Intel設備上的OpenVi-NO與音合成性能測試
audio_s=8.000 infer_s=0.222 rtf=0.028
```

回译存在简繁体、专有名词和近音字差异，但句子主体与原文一致，可确认 CPU 路径生成的语音内容有效。

##### 15.3 NPU 直接加载失败

使用同一模型目录传入 `device=NPU` 时，原始 Pipeline 首先在 Speech Tokenizer Encoder 编译阶段失败：

```text
Upper bounds are not specified
Channels count of input tensor shape and filter shape must be the same
LLVM ERROR: Failed to infer result type(s)
```

CustomVoice 不需要 Speech Tokenizer Encoder。将该 Encoder 改为延迟编译后，Decoder 仍因动态 token 长度无法编译：

```text
Got negative shape dim bound: '-1'
ZE_RESULT_ERROR_INVALID_ARGUMENT
```

再将 Speech Tokenizer 留在 CPU，仅将 Talker 生成主干放到 NPU，Talker Language Model 仍失败：

```text
Upper bounds are not specified for ShapeOf input
to_shape was called on a dynamic shape
```

三级验证说明，该成品 IR 的 Speech Tokenizer Encoder、Decoder 和 Talker 都保留了 NPU 不接受的无上界动态 shape。这不是 NPU 驱动未安装，也不能通过更换 `device` 字符串解决。

##### 15.4 结论

| 路径 | 结果 | RTF | 语音正确性 | 当前可部署 |
| --- | --- | --- | --- | --- |
| 官方 Helper + OpenVINO CPU | 成功 | 1.092 | 通过 ASR 回译 | 可，但略慢于实时 |
| 官方 Helper + OpenVINO NPU | 编译失败 | 无 | 未生成音频 | 不可 |
| Talker=NPU, Tokenizer=CPU | Talker 编译失败 | 无 | 未生成音频 | 不可 |

> 该 Qwen3-TTS 0.6B INT8 成品已成功下载并使用 OpenVINO CPU 加载推理，输出语音有效；但它不是 NPU-ready 静态 shape 模型。若要在 Lunar Lake NPU 上运行，需要按固定 text/token/KV-cache/codec 长度重新导出多个 bucket，而不是直接使用这个动态 IR 成品。

原始日志：

```text
/srv/llm/outputs/benchmarks/qwen3-tts-official/cpu.log
/srv/llm/outputs/benchmarks/qwen3-tts-official/cpu-asr-qc.log
/srv/llm/outputs/benchmarks/qwen3-tts-official/npu.log
/srv/llm/outputs/benchmarks/qwen3-tts-official/npu-lazy-encoder.log
/srv/llm/outputs/benchmarks/qwen3-tts-official/npu-talker-cpu-tokenizer.log
```

#### 16. Intel NPU 实时 TTS 网络方案调研

调研时间：2026-07-15。判定标准为 `RTF < 1.0`，并严格区分“OpenVINO 可运行”、“部分子图使用 NPU”和“全部子图使用 NPU”。

##### 16.1 候选方案排名

| 优先级 | 模型/方案 | NPU 执行方式 | 中文 | 实时证据 | 256V 判定 |
| --- | --- | --- | --- | --- | --- |
| 1 | Kokoro-82M | OpenVINO NPUW，主图 NPU，精度敏感部分 CPU fallback | 支持 | 官方提供 NPU 专用静态 shape 路径，但未公布 256V RTF | 最值得立即实测 |
| 2 | MeloTTS INT8 | BERT=NPU，TTS/VITS 主体=CPU | 支持 | 轻量非自回归，系统级实时概率高，无公开 256V RTF | 追求稳定实时的第二选择 |
| 3 | BabelVox/Qwen3-TTS 0.6B INT8 | Talker/Decoder=NPU，CP/部分 prefill=CPU | 强 | 258V 公开最佳 RTF 1.0；本机正确输出约 1.40 | 需短句分块和流式播放，不能保证 RTF<1 |
| 4 | SpeechT5 + OpenVINO GenAI | API 接受 NPU 设备 | 弱，主要英文 | 无可信 Lunar Lake NPU RTF | 只适合英文兼容性对照 |

##### 16.2 强推荐：Kokoro-82M

OpenVINO 官方最新 Kokoro Notebook 明确要求 OpenVINO 2026.1 或更新版本，并实现了 NPU 专用路径：

```text
input_ids: [1,512]
ref_s: [1,256]
speed: [1]
NPU_USE_NPUW=YES
NPUW_DEVICES=NPU,CPU
NPUW_KOKORO=YES
NPUW_CACHE_DIR=.cache/npuw
```

关键特点：

- 82M 参数，远小于 Qwen3-TTS 0.6B。

- 非大型自回归 Audio LLM，更容易留出 RTF<1 的性能余量。

- NPU 输入被固定为静态 shape，不会重复 Qwen3-TTS 动态 shape 编译失败。

- 官方使用 NPUW 将精度敏感算子回退到 CPU，因此是 NPU+CPU 异构运行，不是严格全 NPU。

- 标准 Kokoro-82M 支持普通话 `lang_code='z'`，需要 `misaki[zh]`，提供 4 个女声和 4 个男声。

- 标准中文音色的模型卡评级偏低，速度可期，但中文音质必须真实验收。

- `Kokoro-82M-v1.1-zh` 额外提供约 100 个中文说话人，但官方 NPU Notebook 默认验证的是标准 Kokoro-82M，中文专版需另行确认导出兼容性。

##### 16.3 可用但不是全 NPU：MeloTTS

Intel/OpenVINO 官方博客的方案是：

```text
Chinese multilingual BERT: NPU, static shape, INT8
MeloTTS/VITS acoustic model: CPU
post-processing/speech enhancement: CPU
```

它支持中文和中英混合，架构较轻，而且不需要像 Qwen3-TTS 一样自回归生成大量 Codec token。如果业务要求是“整体实时”而非“所有子图全 NPU”，MeloTTS 是很实用的候选。

##### 16.4 不建议作为首轮 NPU 实时测试

OpenVINO 官方最新 Notebook 中的设备限制：

| 模型 | 官方 Notebook 当前状态 |
| --- | --- |
| Qwen3-TTS | exclude=["NPU"]，且本机已证实动态 IR 编译失败 |
| FireRedTTS2 | exclude=["NPU"] |
| Parler-TTS | exclude=["NPU"] |
| OpenVoice/OpenVoice2 | exclude=["NPU"] |
| CosyVoice3 | LLM 可选 NPU，Flow 和 HiFT 明确排除 NPU |
| SpeechT5 | OpenVINO GenAI API 可传 NPU，但缺少 256V 实时基准，中文不是优势 |

因此，不能仅根据“OpenVINO Runtime 支持 CPU/GPU/NPU”就认定具体 TTS Pipeline 可在 NPU 上运行。

##### 16.5 本机建议测试顺序

1. **Kokoro-82M 标准版 + OpenVINO 2026.2 + NPUW**：先验证官方 NPU 路径、中文音色、RTF 和 CPU fallback 比例。

2. **Kokoro-82M-v1.1-zh**：若标准版速度达标但中文音质不足，再测试中文专版。

3. **MeloTTS INT8，BERT=NPU + TTS=CPU**：作为中文固定音色和稳定实时基线。

4. BabelVox 只保留为高表达力/声音克隆路线，通过短句 bucket 和流式播放降低感知延迟，不再追求当前 INT8 CP 全 NPU。

来源：

- OpenVINO Kokoro Notebook: [https://github.com/openvinotoolkit/openvino_notebooks/blob/latest/notebooks/kokoro/kokoro.ipynb](https://github.com/openvinotoolkit/openvino_notebooks/blob/latest/notebooks/kokoro/kokoro.ipynb)

- OpenVINO Qwen3-TTS Notebook: [https://github.com/openvinotoolkit/openvino_notebooks/blob/latest/notebooks/qwen3-tts/qwen3-tts.ipynb](https://github.com/openvinotoolkit/openvino_notebooks/blob/latest/notebooks/qwen3-tts/qwen3-tts.ipynb)

- OpenVINO MeloTTS NPU 博客: [https://blog.openvino.ai/blog-posts/optimizing-melotts-for-aipc-deployment-with-openvino-a-lightweight-tts-solution](https://blog.openvino.ai/blog-posts/optimizing-melotts-for-aipc-deployment-with-openvino-a-lightweight-tts-solution)

- BabelVox 模型卡与 258V 基准: [https://huggingface.co/djwarf/babelvox-openvino-int8](https://huggingface.co/djwarf/babelvox-openvino-int8)

- Kokoro 中文音色: [https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md)

- Kokoro 中文专版: [https://huggingface.co/hexgrad/Kokoro-82M-v1.1-zh](https://huggingface.co/hexgrad/Kokoro-82M-v1.1-zh)

#### 17. Kokoro-82M OpenVINO NPUW 与 CPU 实测

测试日期：2026-07-15。

##### 17.1 环境和模型准备

为避免影响现有 LLM、ASR 和 BabelVox 环境，创建独立环境：

```text
/srv/llm/venvs/kokoro-ov
Python 3.12.3
OpenVINO 2026.2.1
torch 2.8.0+cpu
kokoro 0.9.4
misaki 0.9.4 + misaki[zh]
transformers 4.53.3
espeak-ng 1.51
```

使用官方 Notebook 方法从 `hexgrad/Kokoro-82M` 生成动态 OpenVINO IR，再生成 NPU 静态副本：

```text
Dynamic IR: /srv/llm/models/tts/kokoro/Kokoro-82M-openvino
NPU static IR: /srv/llm/models/tts/kokoro/Kokoro-82M-openvino-npu-static
input_ids: [1,512] int64
ref_s: [1,256] float32
speed: [1] float32
```

| 准备阶段 | 耗时 |
| --- | --- |
| PyTorch 源模型加载 | 54.25 s |
| OpenVINO IR 转换 | 13.44 s |
| NPU 静态 reshape/save | 0.17 s |
| 准备进程峰值 RSS | 2,194,460 KiB |

模型大小：

```text
Dynamic IR: 184 MiB
NPU static IR: 184 MiB
NPUW partial cache: 178 MiB
Python environment: 1.7 GiB
```

##### 17.2 NPUW 加载结果：未通过

编译配置与 OpenVINO 官方 Notebook 一致：

```text
device=NPU
NPU_USE_NPUW=YES
NPUW_DEVICES=NPU,CPU
NPUW_KOKORO=YES
NPUW_CACHE_DIR=/srv/llm/.cache/openvino/kokoro-npuw
```

首次 `compile_model` 长时间保持约 100% 单核 CPU，RSS 约 2.1～2.2 GiB，生成 9 个 NPUW cache blob，共 178 MiB；但超过 20 分钟仍未返回，且没有生成首条 WAV。

中断本地 SSH 管道后，发现远端编译子进程未随 SSH 退出，仍持续运行。后续已明确终止本次创建的 PID，并验证无残留测试进程。

使用已有 178 MiB 缓存启动新进程复测，120 秒内仍未完成加载，最终由 timeout 终止：

```text
cache retry limit: 120 s
result: timeout
pipeline status: 137
generated WAV: 0
```

因此不能报告 NPU RTF，也不能认定该方案在当前 Linux/OpenVINO/NPU 驱动组合上可部署。“官方 Notebook 提供 NPU 路径”不等于“当前设备已通过 NPU 性能验证”。

##### 17.3 OpenVINO CPU 干净环境性能

为排除后台 NPUW 编译对 CPU 性能的影响，清理所有残留进程后，在音色已缓存、`HF_HUB_OFFLINE=1` 条件下重新测试 8 个中文音色 × 6 类文本，共 48 例。

| 指标 | 干净环境 CPU 结果 | 目标 | 判定 |
| --- | --- | --- | --- |
| Pipeline compile | 0.670 s | — | 通过 |
| Pipeline init | 0.277 s | — | 通过 |
| RTF mean | 0.183 | ≤0.8 | 通过 |
| RTF median/P50 | 0.180 | ≤0.8 | 通过 |
| RTF P95 | 0.189 | <1.0 | 通过 |
| RTF min | 0.175 | — | — |
| RTF max | 0.288 | <1.0 | 通过 |
| RTF≤0.8 | 48/48 | 48/48 | 通过 |
| RTF<1.0 | 48/48 | 48/48 | 通过 |
| 峰值 RSS | 3,144,108 KiB（约 3.00 GiB） | <2 GiB | 未通过 |
| Swap | 0 | 0 | 通过 |
| 48 例总墙钟 | 79.97 s | — | — |

等效生成速度约为 `1/0.183 = 5.46x` 实时。即使不使用 NPU，该模型在当前 CPU 上也已大幅超过实时目标。

注意：最终干净复测之前的两轮 CPU 测试与残留 NPUW 编译进程并存，其热缓存 P95 为 0.290。该数据作为并发负载下的保守参考，最终结论以清理后的 P95 0.189 为准。

##### 17.4 音色和文本质量

使用已验证的 Whisper Base INT8 NPU Pipeline 对 48 个热缓存 WAV 进行单次加载、批量回译：

```text
ASR load: 0.446 s
files: 48/48
ASR process wall time: 8.51 s
ASR peak RSS: 707,284 KiB
```

质量判定：

- 8 个音色的短句“你好，欢迎回家”均能正确回译。

- `zf_xiaobei`、`zf_xiaoxiao`、`zf_xiaoyi`、`zm_yunxi`、`zm_yunxia`、`zm_yunyang` 的中长中文主体较完整。

- `zf_xiaoni` 的中长文回译错误明显更多，不建议作为默认中文音色。

- 多音字文本的主体普遍可识别，但仍存在“同事/同时”、“长街/长节”等近音误差。

- 长数字序列经常出现位数或数字识别错误；温度、小时、分钟等普通数值语义基本可识别。

- 英文混合文本中 `OpenVINO`、`Intel Core Ultra`、`Kokoro TTS` 的发音/回译错误明显，不适合不经预处理直接播报英文专有名词。

建议默认优先人工试听：

```text
female: zf_xiaoxiao, zf_xiaoyi, zf_xiaobei
male: zm_yunxia, zm_yunyang, zm_yunxi
avoid as default: zf_xiaoni
```

##### 17.5 最终部署判定

| 路径 | 性能 | 质量 | 内存 | 可部署 |
| --- | --- | --- | --- | --- |
| Kokoro OpenVINO NPUW | 未完成加载，无 RTF | 无音频可验证 | 编译约 2.2 GiB | 否 |
| Kokoro OpenVINO CPU | P50 0.180，P95 0.189，约 5.46x 实时 | 中文主体可识别，音色差异大 | 约 3.00 GiB | 是 |

最终结论：

> Kokoro-82M 在当前设备上确实能轻松达到实时，但是通过 OpenVINO CPU 达到，而不是 NPUW。当前 NPUW 路径的加载/编译时间不可接受，不应作为生产方案。产品路径建议使用 OpenVINO CPU，并将 NPU 保留给 Whisper ASR。

原始产物：

```text
/srv/llm/outputs/benchmarks/kokoro-npu/prepare.log
/srv/llm/outputs/benchmarks/kokoro-npu/run-cold.log
/srv/llm/outputs/benchmarks/kokoro-npu/run-npu-cache-retry.log
/srv/llm/outputs/benchmarks/kokoro-npu/run-cpu/metrics.csv
/srv/llm/outputs/benchmarks/kokoro-npu/run-cpu/asr-quality.csv
/srv/llm/outputs/benchmarks/kokoro-npu/run-cpu-clean/metrics.csv
/srv/llm/outputs/benchmarks/kokoro-npu/run-cpu-clean/summary.json
```

Qwen3.5-9B INT4 IR 多模态视觉推理测试报告（私人页面链接不公开）

Qwen3.5-9B + TTS + ASR 测试报告（私人页面链接不公开）

Qwen3.5-4B INT4 VLM 测试报告（私人页面链接不公开）

## R36 · Qwen3.5-9B INT4 IR 多模态视觉推理测试报告

[原笔记图片：微信图片_20260721112741_277_2.jpg；未公开转存]

[原笔记图片：微信图片_20260721112740_276_2.jpg；未公开转存]

### ======================================================================
Qwen3.5-9B INT4 IR 多模态视觉推理测试报告
设备：Windows 11 25H2 / Intel Arc 130V GPU (8GB)
日期：2026-07-21

#### 一、环境信息

OS              Windows 11 25H2

CPU             Intel Core Ultra (Lunar Lake)

GPU             Intel(R) Arc(TM) 130V GPU (8GB) (iGPU)

GPU Driver      32.0.101.8509 (DCH)

Python          3.10.11

OpenVINO        2026.2.1

OpenVINO GenAI  2026.2.1.0

OpenVINO Tokenizers  2026.2.1.0

Optimum Intel   2.0.0

Transformers    5.0.0

Torch           2.13.0

可用设备        CPU, GPU, NPU

模型            OpenVINO/Qwen3.5-9B-int4-ov (INT4 ASYM, group size 128)

模型路径        C:/llm\models\openvino\Qwen3.5-9B-int4-ov

### ======================================================================
二、多图品牌对比测试

测试图片：

- 1.jpg (1920x1080) - POKKA 绿茶瓶

- 2.jpg (1920x1080) - POKKA 草莓味瓶

---

#### Test 1: 品牌识别与对比

Prompt:

图片1和图片2中分别是什么品牌的瓶子？请详细对比两种瓶子的品牌、外观、颜色、瓶身设计、标签文字等方面的区别。

Model Output:

用户要求我识别图片1和图片2中的瓶子品牌，并详细对比它们的外观。

第一步：识别图片1中的瓶子

- 观察：这是一个绿色的瓶子，放在木质桌面上。

- 品牌：瓶身上有明显的红色字样 "POKKA"，是图像中的品牌文字；该私人输入不作为公开验收样本。

- 产品：瓶身标签上写有中文"绿茶"和英文"GREEN TEA"。

- 颜色：瓶身主要是绿色，配有黄色装饰，代表绿茶。

- 瓶盖：白色瓶盖。

- 标签细节：有"无咖啡因"(NO CAFFEINE) 的标志，以及 "LIGHT REFRESHING" 的字样。

第二步：识别图片2中的瓶子

- 观察：这是一个粉橙色瓶子，放在木质桌面上。

- 品牌：瓶身上也有"POKKA"字样，虽然位置和上一瓶一致，属于同一品牌。

- 产品：看起来是草莓味或混合水果味的饮料，瓶身上写有 "ICE" 和 "STRAWBERRY" 字样。

Performance:

Input tokens:      4,125

Generated tokens:  256

TTFT:              13,931 ms

TPOT:              59.9 ms/token

Throughput:        16.70 tokens/s

Inference time:    29.2 s

---

#### Test 2: 细节差异分析

Prompt:

请仔细观察图片1和图片2中的两个瓶子，指出它们的所有不同之处，包括但不限于：品牌名称、瓶子形状、瓶盖颜色、标签设计、容量标注。

Model Output:

用户要求我仔细观察图片1和图片2中的两个瓶子，并指出它们的所有不同之处。

图片1：

- 品牌名称：瓶身上有红色的 "POKKA" 字样。

- 瓶子形状：这是一个典型的塑料饮料瓶，瓶顶较圆，瓶身较细。

- 瓶盖颜色：瓶盖是白色的。

- 标签设计：标签主要是黄绿色，上面写有中文"绿茶"和英文"GREEN TEA"。标签上还有"无咖啡因"的标识，整体看起来清爽的绿色调。

- 容量标注：瓶身下方似乎有容量标注，虽然比较模糊但大致能认出是500ml左右。

图片2：

- 品牌名称：瓶身上也有 "POKKA" 字样，虽然能看到 "POK" 部分。

- 瓶子形状：瓶子形状与图片1非常相似，也是圆柱形塑料瓶。

- 瓶盖颜色：图片中不太明显，可能也是白色或浅色。

- 标签设计：标签是粉色/橙色为主，写有 "ICE" 和 "STRAWBERRY"。

- 容量标注：类似500ml规格。

对比总结：

两者都是POKKA品牌的即饮茶/饮料产品，但图片1是绿茶味（绿色瓶身），图片2是草莓味（粉色瓶身）。

瓶身形状相同，颜色和标签设计因口味不同而不同。

Performance:

Input tokens:      4,127

Generated tokens:  256

TTFT:              11,844 ms

TPOT:              61.8 ms/token

Throughput:        16.18 tokens/s

Inference time:    27.7 s

### ======================================================================
三、性能优化对比测试

Test image: test_image.png (512x384, colored shapes)

Prompt: "请描述这张图片中有什么，包括颜色、形状和数量。"

---

#### 配置                          加载(s)  吞吐(t/s)  TTFT(ms)  TPOT(ms)

1. BASELINE (默认)             24.70    17.15     1,801.70  58.30

2. CACHE (首次写入)            34.96    16.61     2,363.93  60.22

3. CACHE + THROUGHPUT          35.30    17.08     1,761.16  58.55

4. CACHE + THROUGHPUT + FP16   31.42    17.39     1,339.28  57.51  ★最佳TTFT

5. CACHE + LATENCY             30.77    17.44     1,374.33  57.33  ★最佳吞吐

6. CACHE 热加载 (2nd load)     28.22    17.21     1,358.52  58.10

---

最优配置：

PERFORMANCE_HINT = "LATENCY"

INFERENCE_PRECISION_HINT = "f16"

TTFT 改善：1,802ms → 1,339ms（-25.7%）

### ======================================================================
四、纯文本推理基线

Model Output (text-only, no image):

用户要求用中文简要说明人工智能推理加速的作用。

1. 分析请求：

  - 主题：人工智能推理加速

  - 任务：简要说明其作用

  - 语言：中文

2. 定义"AI推理加速"：

  - 它是什么？它是使AI模型的"推理"阶段变得更快更高效的过程。

  - 什么是"推理"？它是...

Performance:

Input tokens:      19

Generated tokens:  128

Throughput:        17.34 t/s

TTFT:              488 ms

TPOT:              57.7 ms/token

### ======================================================================
五、总结

1. 多模态视觉推理：✅ 成功

  - 单图描述、VQA 均正常

  - 多图对比推理正常，正确区分了同一品牌的不同产品

2. 推理吞吐：17.34 t/s（纯文本）/ 16.70 t/s（双图）

  - 超过 12 t/s 生产目标

  - 约为 Linux/Mesa 26.1.4 参考性能的 82%

3. 优化效果：

  - TTFT 降低 25.7%（f16 精度提示）

  - 吞吐提升 1.7%（LATENCY 性能提示）

  - 模型缓存可减少加载时间约 5%

4. NPU 不可用（参考 Ubuntu 部署报告已证实编译失败）

  - 当前仅使用 GPU 推理

5. 推荐生产配置：

  pipe = VLMPipeline(model, "GPU",

  PERFORMANCE_HINT="LATENCY",

  INFERENCE_PRECISION_HINT="f16",

  )

======================================================================

## R37 · 使用ipex-llm进行量化并制作ollama模型，部署在Intel集显。

ipex-llm链接：[https://ipex-llm-latest.readthedocs.io/en/latest/doc/LLM/Quickstart/ollama_quickstart.html](https://ipex-llm-latest.readthedocs.io/en/latest/doc/LLM/Quickstart/ollama_quickstart.html)

1. 创建conda环境，并下载ipex-llm，注意提前下载好Intel驱动，可在链接中查看。

```text
conda create -n llm-cpp python=3.11
conda activate llm-cpp
pip install --pre --upgrade ipex-llm[cpp]
```

1. 创建一个llama-cpp目录，并进入该目录。

```text
mkdir llama-cpp
cd llama-cpp
```

1. 根据量化教程量化模型

2. 使用管理员权限打开cmd

- 请**在 Miniforge Prompt 中使用管理员权限** 运行以下命令。

  ```text
  conda activate llm-cpp
  init-ollama.bat

  ```

1. 启动ollama服务

- 请在 Miniforge Prompt 中运行以下命令。

  ```text
  set OLLAMA_NUM_GPU=999
  set no_proxy=localhost,127.0.0.1
  set ZES_ENABLE_SYSMAN=1
  set SYCL_CACHE_PERSISTENT=1
  rem under most circumstances, the following environment variable may improve performance, but sometimes this may also cause performance degradation
  set SYCL_PI_LEVEL_ZERO_USE_IMMEDIATE_COMMANDLISTS=1

  ollama serve
  ```

Note：请设置环境变量 `OLLAMA_NUM_GPU` 为 `999` 确保模型的所有层都在 Intel GPU 上运行，否则某些层可能会在 CPU 上运行。

1. 创建Modelfile文件

Ollama 支持在 Modelfile 中导入 GGUF 模型，例如，假设你已经从 [Mistral-7B-Instruct-v0.1-GGUF](https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.1-GGUF/tree/main) 下载了 `mistral-7b-instruct-v0.1.Q4_K_M.gguf`，那么你可以创建一个名为 `Modelfile` 的文件:

```text
FROM ./mistral-7b-instruct-v0.1.Q4_K_M.gguf
TEMPLATE [INST] {{ .Prompt }} [/INST]
PARAMETER num_predict 64
```

然后，你可以在 Ollama 中通过 `ollama create example -f Modelfile` 创建模型，并使用 `ollama run` 直接在控制台运行该模型。

1. 运行模型

请在 Miniforge Prompt 中运行下列命令。

```text
set no_proxy=localhost,127.0.0.1
ollama create example -f Modelfile
ollama run example
```

## R38 · Intel NPU进行模型推理：deepseek-r1:1.5b,7b,8b

参考链接：[https://www.51openlab.com/article/728/](https://www.51openlab.com/article/728/)

本技术文档详细介绍了如何在配备Intel Core Ultra处理器的设备上，利用其强大的神经处理单元(NPU)部署DeepSeek-R1系列大语言模型（1.5B/7B/8B）。通过OpenVINO™ GenAI技术栈，我们将展示从环境搭建到模型量化、再到NPU推理的完整部署方案。

1. 搭建环境

  1.1 创建conda环境

  ```text
  #创建环境
  conda create -n 环境名称 python=3.10
  #激活环境
  conda activate 环境名称
  ```

  1.2 搭建OpenVINOTM GenAI开发环境

  ```text
  # 安装OpenVINO GenAI

  pip install openvino-genai

  # 安装optimum-intel，用于转换并量化生成式AI模型

  pip install optimum-intel[openvino]
  ```

2. 下载模型并进行量化模型（转成openvineo格式）

  2.1 下载模型

  ```text
  # 安装ModelScope

  pip install modelscope

  # 下载DeepSeek-R1-Distill-Qwen-1.5B模型到指定

  modelscope download --model deepseek‑ai/DeepSeek‑R1‑Distill‑Qwen‑1.5B --local_dir "C:/llm\Desktop\llm-NPU"

  #下载8b-0528
  modelscope download --model deepseek-ai/DeepSeek-R1-0528-Qwen3-8B --local_dir "C:/llm\Desktop\llm-NPU\ds-8b-0528"

  # 下载ds-8b
  modelscope download --model deepseek-ai/DeepSeek-R1-Distill-Llama-8B --local_dir "C:/llm\Desktop\llm-NPU\ds-8b"
  ```

  2.2 使用optimum-cli进行模型量化并转换格式

  ```text
  optimum-cli export openvino
    --model C:/llm\Desktop\llm-NPU\deepseek-r1-1_5
    --task text-generation-with-past
    --weight-format int4
    --sym
    --ratio 1.0
    --group-size 128
    C:/llm\Desktop\llm-NPU\deepseek-r1-1_5-openvino


    #转换并量化ds-8b
    optimum-cli export openvino --model "C:/llm\Desktop\llm-NPU\ds-8b" --task text-generation-with-past --weight-format int4 --sym --ratio 1.0 --group-size -1 "C:/llm\Desktop\llm-NPU\ds-8b-openvino"
  ```

1. 推理和测试脚本

  ```text
  import openvino_genai as ov_genai

  # 创建 LLMPipeline 对象，指定模型路径和设备类型
  pipe = ov_genai.LLMPipeline(r"C:/llm\Desktop\llm-NPU\deepseek-r1-1_5-openvino", "NPU")

  # 定义流式输出的回调函数
  def streamer(subword):
      print(subword, end='', flush=True)
      # 返回状态，指示生成是否继续
      return ov_genai.StreamingStatus.RUNNING

  # 启动对话
  pipe.start_chat()

  # 提示用户输入问题
  while True:
      try:
          prompt = input('问题：\n')
      except EOFError:
          break
      # 调用 generate 方法进行生成，并传入回调函数
      pipe.generate(prompt, streamer=streamer, max_new_tokens=4096)
      print('\n----------\n')

  # 结束对话
  pipe.finish_chat()

  ```
