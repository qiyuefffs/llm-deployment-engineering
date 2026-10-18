# 第 3 层：推理框架层

[总目录](../README.md) · [上一层：模型与量化](02-model-formats-quantization.md) · [下一层：显存与性能](04-memory-performance.md)

## 3.1 推理框架解决什么问题？

模型文件保存参数，推理框架负责把参数变成计算：读取模型、分配内存、执行算子、管理 KV、调度请求，最后返回生成结果。服务端还要处理模板、流式传输、异常和并发。

选择框架先看任务和设备，再看吞吐。一个速度快但不支持目标量化、视觉输入或所需上下文的框架，无法完成部署。

| 路线 | 常见输入 | 优先考虑的场景 | 首先验证 |
| --- | --- | --- | --- |
| vLLM | 受支持的 HF 权重与量化制品 | 在线服务、多请求、设备计算能力较强 | 模型结构、kernel、设备后端、调度和接口 |
| llama.cpp | 受支持的 GGUF | CPU、端侧、部分卸载、多种后端 | 架构、量化类型、实际卸载、上下文与槽位 |
| OpenVINO GenAI | 配套 IR 与 tokenizer | Intel CPU/GPU/NPU 路线 | 插件、模型图、设备编译、任务 Pipeline |
| MLX-LM / MLX-VLM | 受支持的 MLX 模型 | Apple Silicon 本机推理 | 文本/视觉库、布局、内存、版本 |
| oMLX 等服务层 | 对应引擎支持的模型 | Apple 本地多请求服务 | 引擎版本、模型发现、调度、缓存、API |
| TensorRT-LLM 等 | 对应构建或加载格式 | NVIDIA 特定部署与优化 | GPU 架构、精度、模型支持、构建配置 |

“兼容 OpenAI API”描述接口形状，不保证工具调用、视觉、结构化输出和错误行为完全一致。使用前列出应用真正会调用的功能，逐项验证。

## 3.2 vLLM 的运行结构

可以按下面这条请求链理解：

```text
HTTP 请求 → 参数检查 → Chat Template / Tokenizer
 → 调度器 → KV 分配与缓存 → 模型执行器 / 设备 kernel
 → Detokenizer → 流式片段或完整响应
```

调度器决定这一轮哪些请求执行、处理多少输入 token、哪些请求继续生成。模型执行器负责在设备上计算；KV 管理器保存已处理 token 的状态。这几部分共同决定吞吐和延迟，不能把所有性能变化都归因于某个注意力算子。

启动日志要看四件事：加载的是哪份模型；实际使用哪个后端和精度；留出多少 KV；图捕获、编译和 warm-up 是否完成。进程存在不等于服务已准备好。

### 五个常用参数

| 参数 | 控制内容 | 配置时的判断 |
| --- | --- | --- |
| `--max-model-len` | 单个序列允许的总长度 | 输入、历史、模板和预期输出要一起算 |
| `--max-num-seqs` | 引擎可调度的最大序列数 | 增大会增加资源需求，不保证线性提升吞吐 |
| `--max-num-batched-tokens` | 一轮调度的 token 预算 | 影响 prefill 分块、decode 干扰与执行效率 |
| `--gpu-memory-utilization` | 引擎采用的设备内存预算比例 | 需给系统、图、其他进程和波动留空间 |
| `--kv-cache-dtype` | KV 数据类型 | 需要后端支持，并单独做质量与长上下文回归 |

参数含义和默认值会随版本变化。将实际版本的 `vllm serve --help` 保存为交付材料，再写配置；不要把旧教程中的开关直接套到新版本。

## 3.3 vLLM：从启动到第一次 API 请求

### 实例环境

FlowUs 的 GB10 工程记录 E01 使用 DGX Spark 128GB、Ubuntu 24.04 ARM64、CUDA 13.0，vLLM `0.19.1rc1.dev337+g17d87168d.cu130`。目标为 `Qwen3.6-35B-A3B-FP8`。安装配套关系见[硬件层](01-hardware-backends.md)，模型准备见[模型层](02-model-formats-quantization.md)。

以下是该记录的公开路径改写，默认仅在本机提供服务。模型已经放在 `/srv/models/Qwen3.6-35B-A3B-FP8`，当前 shell 已进入对应 vLLM 环境。

```bash
mkdir -p logs
vllm --version
vllm serve --help > logs/vllm-serve-help.txt
vllm serve /srv/models/Qwen3.6-35B-A3B-FP8 \
  --served-model-name Qwen3.6-35B-A3B-FP8 \
  --host 127.0.0.1 --port 8001 \
  --max-model-len 16184 \
  --max-num-batched-tokens 8192 \
  --max-num-seqs 4 \
  --gpu-memory-utilization 0.80 \
  --generation-config auto \
  --override-generation-config '{"temperature":0.6,"top_p":0.95,"top_k":20}' \
  --kv-cache-dtype fp8 \
  --load-format auto \
  --attention-backend flashinfer \
  --enable-prefix-caching \
  --enable-chunked-prefill \
  2>&1 | tee logs/vllm-server.log
```

原记录包含 `--trust-remote-code`。只有模型确需仓库代码、且已经审阅并固定版本时才加；它不是所有模型的必要选项。上面的命令保留历史性能相关参数，不代表其他设备的起步配置。

在第二个终端验证：

```bash
curl --fail-with-body http://127.0.0.1:8001/health
curl --fail-with-body http://127.0.0.1:8001/v1/models
curl --fail-with-body http://127.0.0.1:8001/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"Qwen3.6-35B-A3B-FP8","messages":[{"role":"user","content":"用三点说明部署模型前为什么要检查可用内存。"}],"max_tokens":256,"temperature":0,"stream":false}'
```

检查顺序：服务 ready；模型列表有正确别名；返回文本非空；内容符合任务；`finish_reason` 和实际 token 数合理。推理模型可能先生成思考内容，`max_tokens` 太短会在回答前截断。看到 HTTP 200 后还要检查完整答案。

**路径与别名的区别：** `/srv/models/...` 是服务器读取文件的位置，`--served-model-name` 是客户端填写的模型标识。压测的 tokenizer 必须指向匹配的 tokenizer，不能拿服务别名当成一定可下载的仓库名。

### 再验证流式

把请求中的 `stream` 改为 `true`，curl 增加 `-N`。先保存完整 SSE 内容，检查是否分段到达、有没有终止标记、是否包含错误。应用端应按 SSE 事件解析 JSON，不能假设“一行就是一个 token”，也不能把空事件当成生成内容。

### 再验证异常

提交不存在的模型别名、缺少 `messages` 的请求、超过上下文的输入，分别记录 HTTP 状态与错误体。正常响应和错误响应都要有检查；代理层不能把上游错误包装成成功文本。

## 3.4 llama.cpp 的结构

```text
GGUF 解析 → 模型图 → GGML 后端 → 内存与 KV → 生成采样
                                    ↘ CLI / Benchmark / HTTP Server
```

常用程序有不同用途：

| 程序 | 用途 | 不能据此直接证明 |
| --- | --- | --- |
| `llama-cli` | 单次生成、模型和后端冒烟 | 多请求服务能力 |
| `llama-bench` | 控制 pp/tg 等引擎负载 | HTTP 首 token 延迟和业务质量 |
| `llama-server` | 提供接口和调度请求 | 只启动成功就满足目标并发 |
| `llama-quantize` | 将支持的权重转换成量化类型 | 所有硬件都有对应高效 kernel |
| `rpc-server` | 向主进程提供远端后端资源 | 任意模型在网络上都有加速收益 |

`-ngl` 是卸载层数请求；实际卸载、每层放置与缓冲分配以日志为准。MoE、视觉投影、输出层和不同内存类型会使“层数占比”与“字节占比”不同。

## 3.5 llama.cpp：构建、单次运行与服务

### 固定源码并分后端构建

E03 使用的源码为 `0f7fada56`，版本标记 `b9557`。以下以它说明固定版本与分目录构建的方法。其他模型应先确认该提交支持目标架构，不能为了复用版本强行转换。

```bash
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp
git checkout 0f7fada56
git rev-parse HEAD
```

各段命令选择一条执行；需先装好对应 SDK、驱动与构建依赖。

```bash
# CUDA：先核对设备计算能力与此提交的构建要求
cmake -S . -B build-cuda -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build-cuda --target llama-cli llama-server llama-bench -j 4
```

```bash
# HIP：gfx1151 对应记录中的 AMD 8060S
cmake -S . -B build-hip -DGGML_HIP=ON \
  -DAMDGPU_TARGETS=gfx1151 -DCMAKE_BUILD_TYPE=Release
cmake --build build-hip --target llama-cli llama-server llama-bench -j 4
```

```bash
# Vulkan
cmake -S . -B build-vulkan -DGGML_VULKAN=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build-vulkan --target llama-cli llama-server llama-bench -j 4
```

```bash
# macOS / Metal
cmake -S . -B build-metal -DGGML_METAL=ON \
  -DGGML_ACCELERATE=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build-metal --target llama-cli llama-server llama-bench -j 4
```

每次保留 `CMakeCache.txt`、编译日志、完整 commit 和程序 `--version`。出现未使用的 CMake 变量要查明原因。配置完成后还要真正运行 `cmake --build`。

### 先 CLI，后服务

以下用 HIP 构建举例。`MODEL` 指向已经验证兼容的 GGUF；路径仅为部署约定，不提供未经确认的权重下载。

```bash
export MODEL=/srv/models/model.gguf
./build-hip/bin/llama-cli --help > llama-cli-help.txt
./build-hip/bin/llama-cli -m "$MODEL" -ngl 99 -c 2048 -n 64 \
  -p '请说明模型推理中权重与KV缓存的区别。'
```

通过后再开启服务：

```bash
./build-hip/bin/llama-server -m "$MODEL" \
  --host 127.0.0.1 --port 8080 \
  -ngl 99 -c 4096 -np 1
```

先单槽位验收，再增加 `-np`。不同版本的上下文总预算、槽位划分和统一 KV 行为可能不同；根据启动日志核对每个请求真正可用的上下文，不能只看 `-c` 数字。

用 `/health`、`/v1/models` 与 `/v1/chat/completions` 复用上一节的验证方法。模型字段使用 `/v1/models` 返回的标识，或使用该版本支持的显式别名选项。

### 引擎基准

```bash
./build-hip/bin/llama-bench -m "$MODEL" -ngl 99 -p 512 -n 128 -r 3
```

将 pp512 与 tg128 分开看。记录 CPU 线程、后端、卸载层数、输入输出长度及缓存条件；不要把 tg token/s 写成含网络和排队的端到端吞吐。

## 3.6 框架选型的实际判断顺序

1. **能否正确执行：** 架构、精度、算子、视觉/工具功能是否支持。
2. **资源是否可容纳：** 权重、KV、缓冲与操作系统能否共存。
3. **接口是否满足应用：** 模板、流式、取消、结构化结果、错误是否一致。
4. **目标负载是否达标：** 单请求速度与目标并发分别测试。
5. **是否便于交付：** 安装、版本、监控、重启与回滚能否固定。

Intel 记录 E02 中，OpenVINO IR GPU 管线完成生成；NPU 路线分别出现编译失败和超时。这里可以选择 GPU 路线继续交付，保留 NPU 失败条件；无需为了使用 NPU 标签而反复扩大测试范围。

## 3.7 OpenVINO GenAI：IR → GPU → 输出与指标

E02 环境为 Core Ultra 7 256V / Arc Lunar Lake / 16GB，Ubuntu 24.04.4。已下载的 INT4 IR 放在 `/srv/models/Qwen3.5-9B-int4-ov`；固定 revision 和文件校验见上一层。

```bash
python3 -m venv .venv-ov
source .venv-ov/bin/activate
python -m pip install openvino==2026.2.1 \
  openvino-genai==2026.2.1.0 openvino-tokenizers==2026.2.1.0
python -m pip freeze > openvino-environment.txt
```

保存为 `run_openvino.py`：

```python
import openvino as ov
import openvino_genai as genai

print('devices:', ov.Core().available_devices)
pipe = genai.VLMPipeline('/srv/models/Qwen3.5-9B-int4-ov', 'GPU')
pipe.generate('Hello', max_new_tokens=8, do_sample=False)
result = pipe.generate(
    '请用中文简要说明人工智能推理加速的作用。',
    max_new_tokens=128, do_sample=False,
)
print(result)
m = result.perf_metrics
print('input tokens:', m.get_num_input_tokens())
print('generated tokens:', m.get_num_generated_tokens())
print('TTFT ms:', m.get_ttft().mean)
print('TPOT ms:', m.get_tpot().mean)
print('throughput token/s:', m.get_throughput().mean)
```

```bash
python run_openvino.py > openvino-result.txt 2>&1
```

模型带多模态结构，因此记录使用 `VLMPipeline`，即使本次只输入文本。不要未经核对改成另一种 Pipeline。检查设备编译、生成 token、输出内容和性能字段；该计时属于 Pipeline 内部口径，首次加载与编译时间应额外记录。

原记录 INT4 为 21.1599 token/s、INT8 为 10.1047 token/s，均在 128 token 上限的思考阶段结束。它证明完成了受限生成，完整答案质量仍需补测。

## 3.8 Apple：制品与服务层分开理解

MLX 与 GGUF 是两条部署路线。MLX-LM 处理受支持的文本模型，MLX-VLM 还涉及视觉处理；llama.cpp 使用自己的 GGUF 和 Metal kernel。不要将一条路线转换出的目录直接交给另一条。

oMLX 是服务入口之一。源笔记中 `--model-dir` 用模型父目录，服务会发现其中模型；传入内部子目录可能导致发现失败。实际命令以固定版本的帮助为准，保存可用模型列表，再完成正常、流式和并发请求。

E05 的 vllm-metal 组合为 Python 3.12.13、vllm-metal 0.2.0、vLLM 0.21.0+cpu、MLX 0.31.2。文本成功，而图片请求报视觉 encoder 尚未接通。因此应分别记录文本与视觉能力。

另一个 Metal 工程使用特殊分支 `9d36408`，特定 FP4/FP8 制品在执行时发生 type 42 断言。编译成功不能代替模型运行；也不能把这一组合的失败扩大为所有 Metal 模型都失败。

## 3.9 模板、采样和功能要单独验收

| 项目 | 验证方法 | 常见问题 |
| --- | --- | --- |
| Chat Template | 查看模型自带模板，以同一对话测试 | 重复套模板、角色标记泄漏、停止不正确 |
| 推理内容 | 分别查看思考与最终答案 | token 上限耗在思考中，最终正文为空 |
| 采样 | 固定 temperature、top_p、top_k、seed | 服务默认 generation config 覆盖预期 |
| 流式 | 保存 SSE 并记录客户端到达时间 | 代理缓冲、多个 token 合并、空事件计时 |
| 工具调用 | 检查解析出的结构与实际函数参数 | 有工具文本却无可用结构 |
| 视觉 | 同一张有权使用的图片与明确任务 | 只启动文本后端，缺预处理或投影模型 |
| 结构化输出 | 解析并按 JSON Schema 检查 | 合法 JSON 但字段语义错误 |

质量回归时保存模型 revision、模板、生成参数与原始请求。固定 seed 不保证不同后端逐 token 一致，验收应围绕任务正确性。

## 3.10 多卡、多节点与模型切分

| 方式 | 怎样分工 | 适用条件与代价 |
| --- | --- | --- |
| TP | 一个算子或张量跨设备分片 | 通信频繁，依赖拓扑和模型维度 |
| PP | 不同层或阶段放不同设备 | 有流水线气泡，调度与负载影响收益 |
| DP | 多个完整副本处理不同请求 | 提高总服务能力，通常不降低单请求权重需求 |
| EP | MoE 专家分布到不同设备 | 路由、专家负载和 all-to-all 成本需要分析 |
| llama.cpp RPC | 主进程调用远端设备后端 | 扩展可用容量，网络和分层方案影响速度 |

RTX 4080 不支持 NVLink。E11 旧笔记中的“安装 NVLink 桥”应纠正；双卡部署仍应检查 PCIe 拓扑、P2P 和通信实测。不能因为总显存相加够用，就认定所有 kernel 与通信都支持。

多设备执行顺序：**每台小算子 → 通信正确性 → 小模型 → 目标模型短请求 → 目标长度 → API 并发**。通信检查脚本见 [all_reduce_check.py](../examples/all_reduce_check.py)，需在已配置的 CUDA/NCCL 环境实际运行。

### AMD 五机 RPC 工程怎样用

E03 的五台 395 设备使用 `gfx1151`、ROCm 7.2.1、上述 llama.cpp 提交，构建增加 `-DGGML_RPC=ON`。它解决模型容量问题，先用小上下文验收。RPC worker 端口为 50053，远程地址应在私有受控网络配置；示例地址可写 `192.0.2.11:50053` 等文档保留地址，运行时替换为自己的配置。

RPC 参数包含四个远端与本机分配比例：

```text
--split-mode layer
--tensor-split 0.143,0.21425,0.21425,0.21425,0.21425
--rpc <四个工作节点的地址与端口>
--no-mmap -c 512 -b 32 -ub 8 -fa off
```

这是历史小上下文配置节选。原记录 Kimi 生成约 8.2 token/s，但缺单机基线与长期 API 测试，不能据此计算五机加速比。编译了 RDMA 选项也不代表实际走 RDMA；确认运行日志与网络路径。

## 3.11 本层完成标准

交付固定框架环境、模型路径与身份、完整启动命令、实际后端日志和功能矩阵。单次生成、HTTP 正常请求、流式、错误输入分别通过后，再进入[显存与性能优化](04-memory-performance.md)。

实例条件和数据缺口统一查 [E01～E14 来源索引](../evidence/README.md)。
