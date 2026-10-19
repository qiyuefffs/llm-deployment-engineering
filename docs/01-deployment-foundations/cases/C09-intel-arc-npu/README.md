---
id: C09
title: "Intel Arc与NPU：Vulkan、SYCL、IR和语音任务完整对照"
type: case
volume: cases
layer: 1
platform: "Intel"
device: "Arc / NPU"
status: historical
source_ids: [R35, R36, R37, R38]
updated: 2026-10-19
summary: "技术标签：Core Ultra 7 256V / 16GB / OpenVINO / ASR / TTS"
---

# Intel Arc与NPU：Vulkan、SYCL、IR和语音任务完整对照

[工程实例索引](../README.md) · [知识体系总目录](../../SUMMARY.md)

技术标签：`Core Ultra 7 256V / 16GB / OpenVINO / ASR / TTS`

## 结论

同 GGUF 的 Vulkan/SYCL 三轮引擎 Decode 为 11.54±0.13 / 10.22±0.19
tok/s。OpenVINO IR 的 INT4/INT8 在同19输入、128输出下生成吞吐为
21.16±0.71 / 10.10±0.18 tok/s，但输出仍在 thinking 阶段，最终答案未验收。
NPU 编译失败或超时的组保留为失败，没有 NPU LLM 吞吐值。

## 适用边界

16GB 共享内存的 Core Ultra 7 256V / Arc Lunar Lake / NPU；GPU、NPU、
Windows IPEX-LLM 与 Linux OpenVINO 都是独立组合。GGUF、IR 与 API
计时边界不同，绝对速度不直接合成一个严格排名。

## 环境与制品

| 项目 | 已记录条件 |
| --- | --- |
| 设备 | Core Ultra7 256V，Arc Lunar Lake GPU，NPU，16GB共享内存 |
| 系统 / 工具 | Ubuntu24.04.4、Mesa26.1.4、oneAPI2026.1.0、OpenVINO2026.2.1 |
| GGUF | llama.cpp Vulkan与SYCL；GPU23层/CPU10层，pp512/tg128三轮 |
| IR | Qwen3.5-9B INT4/INT8固定revision与文件清单 |
| 语音 | Whisper ASR、BabelVox混合TTS、全NPU实验、Qwen3-TTS与Kokoro48例 |

## 执行路径

```text
驱动与设备枚举 → 独立Vulkan/SYCL构建 → 同GGUF分层与pp/tg
 → IR文件校验 → GenAI GPU管线 → 功能完整性
 → NPU编译和shape检查 → 语音分模块 → 完整音频质量 → RTF与RSS
```

GPU、NPU是不同执行目标，不能只把device字符串改掉就沿用GPU成功结论。NPU编译失败、超时、fallback、错误音频和CPU成功分别记录。Windows IPEX-LLM/Ollama属于另一版本组合，不混入Linux基线。

### GGUF 测试要保持分层与轮数一致

R35 两种后端使用同一 Qwen3.5-9B Q4_K_M、GPU23层/CPU10层，
`t=8, fa=on, pp512, tg128, r=3`。核对每份日志的实际卸载和驱动版本，
再比较 pp/tg。旧 Mesa 的结果另存，不把升级与后端变化合成单一因素。

### OpenVINO 的实际最小测量

下面来自 R35；模型路径使用公开约定位置。先确认官方 IR 的 revision、
24个文件及总字节数，再建立 pipeline，不使用尚不兼容的 GGUF backend。

```python
import openvino_genai as ov_genai

model = "/srv/llm/models/openvino/Qwen3.5-9B-int4-ov"
pipe = ov_genai.VLMPipeline(model, "GPU")
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

INT8 只替换对应 IR 目录，保留 prompt、warm-up 和生成参数。计时来自
GenAI PerfMetrics，不能与 HTTP 端到端时间混名。若复制到 NPU，需重新
记录编译和实际生成阶段，设备枚举成功不是任务成功。

## 结果

| 实验 | 观测 | 工程判断 |
| --- | --- | --- |
| IR INT4/INT8 GPU | 固定输入的生成速率观察比值约2.09 | 输出处于思考截断阶段，质量未完成 |
| Vulkan/SYCL | 同pp/tg与23/10层对比 | 引擎时间不与HTTP直接排名 |
| Whisper NPU | 4.4s音频，三轮核心时间约0.17s | 进程冷启动另记，核心RTF约0.039 |
| BabelVox全NPU | 性能达标，音频内容错误 | 质量失败，回滚混合路径 |
| Kokoro CPU | 48例、P95 RTF0.189、约3GiB RSS | 实时目标通过，原内存目标失败 |
| Kokoro NPUW | 首次超过20分钟，缓存复测120s超时 | 无WAV，不能报告NPU吞吐 |

验收分四项：功能完整、内容正确、实时性、内存预算。全NPU和最低RTF不是最终目标；失败方案保留输入shape、编译配置和退出状态，便于下一版回归。

| LLM 路线 | 关键结果 | 计时边界 |
| --- | --- | --- |
| Vulkan | pp244.91±0.79，tg11.54±0.13 tok/s | pp512/tg128，3轮 |
| SYCL | pp353.70±15.31，tg10.22±0.19 tok/s | 同一 GGUF 和分层 |
| INT4 IR GPU | TTFT184.02 ms，TPOT47.26 ms/token | GenAI，19/128 tokens |
| INT8 IR GPU | TTFT169.73 ms，TPOT98.96 ms/token | 同任务，最终答案未完成 |
| INT4 NPU | `Found 32 duplicated names` | 编译失败，未生成 |
| INT8 NPU | 420 s 超时，退出124 | 编译未完成，未生成 |

## 失败与修订

INT4/INT8 的吞吐观察可用于性能候选筛选，但 reasoning 截断说明业务功能
尚未完整通过。llama.cpp OpenVINO WIP 虽可编译和枚举，在 `cache_r_l0` /
`CPY` 图操作处失败，也不能当成 IR GPU 的成功证据。

语音任务用实际音频时长计算 RTF，冷进程启动单独记录。BabelVox 全 NPU
虽性能达标但音频错误，Kokoro CPU 虽实时却超过原内存目标，这些都需要
进入最终验收；没有 WAV 的 NPU 超时组没有有效 RTF。

## 证据

- [R35 完整技术正文](../../evidence/sources/R35.md)
- [R36 完整技术正文](../../evidence/sources/R36.md)
- [R37 完整技术正文](../../evidence/sources/R37.md)
- [R38 完整技术正文](../../evidence/sources/R38.md)

## 未验证

LLM 最终答案、多轮长文、并发与长期内存压力尚未齐备。NPU 失败组需等待
具体编译器/算子修订后重测；不能用 GPU 成功补填。原模型摘要只在本地清单核对。

数据来源与边界见[证据使用说明](../../meta/evidence-policy.md)。
