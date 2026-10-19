---
id: T23
title: "当前推理引擎怎么选：先匹配执行路径，再比较服务结果"
type: tutorial
volume: book
layer: 3
platform: "general"
device: "general"
status: historical
source_ids: []
updated: 2026-10-19
summary: "资料核查：2026-10-18。 这里介绍当前维护中的工程路线；具体支持仍由模型、硬件和固定引擎版本共同决定。"
---

# 当前推理引擎怎么选：先匹配执行路径，再比较服务结果

[总目录](../../SUMMARY.md) · [推理框架总章](../../02-capability-layers/03-inference-frameworks.md) · [量化](../models/quantization.md) · [分离式推理](../performance/disaggregated-serving.md)

**资料核查：2026-10-18。** 这里介绍当前维护中的工程路线；具体支持仍由模型、硬件和固定引擎版本共同决定。

## 1. 一套部署配置需要匹配六项

```text
模型架构 → 权重格式/量化元数据 → 设备与kernel
         → KV/状态实现 → 调度与并行 → 对外接口/解析器
```

“支持Qwen”不足以完成选型。相同系列可能包含dense、MoE、混合attention、视觉、音频与MTP变体。必须查看精确架构与模型卡，再核对量化、草稿模块、工具解析和多模态输入。

| 引擎路线 | 适合优先评估的需求 | 必须核对的执行条件 |
| --- | --- | --- |
| llama.cpp | GGUF、本地运行、CPU/GPU混合、多后端 | 架构、实际卸载、量化张量、槽位和草稿支持 |
| vLLM | 多请求服务、连续批处理、模型并行、推测 | 模型实现、attention/linear/MoE backend、runner与版本 |
| SGLang | 前缀复用、结构化服务、PD/MoE组合 | RadixAttention、scheduler、传输后端与router |
| TensorRT-LLM | NVIDIA上成套kernel、量化和服务优化 | GPU代际、后端、模型、运行制品与容器 |
| MLX-LM/MLX-VLM | Apple Silicon上的文本与视觉 | MLX版本、转换格式、处理器与缓存实现 |
| OpenVINO GenAI | Intel CPU/GPU/NPU生成管线 | IR导出、设备插件、shape与模型覆盖 |

模型可以装入并不代表该引擎是最快选择。完整选型应使用同一任务集、输出口径、设备预算和SLO做对照。

## 2. vLLM：不要继续沿用V0时代的调参习惯

V1的chunked prefill在可用时默认启用，调度通常先放入decode，再用剩余token预算接纳prefill。`max-num-batched-tokens`是每轮token预算，`max-num-seqs`是活动序列预算；两者都不是客户端并发数。

```bash
vllm serve /srv/models/example-model \
  --served-model-name serving-lab \
  --host 127.0.0.1 --port 8000 \
  --max-model-len 8192 --max-num-seqs 8 \
  --max-num-batched-tokens 2048 \
  --enable-chunked-prefill --enable-prefix-caching \
  --gpu-memory-utilization 0.80
```

这是参数教学模板，模型目录需要换成已验收的制品。固定其他条件，只扫2048/4096/8192三档batched tokens。较小预算可能减少单轮prefill对decode的干扰，较大预算可能改善prefill完成时间；方向要以实际混合负载验证。

不要照旧笔记一律加`--enforce-eager`。它适合隔离编译/图问题，但会改变稳定性能，并与部分新机制冲突。先保存可工作的普通生成基线，再比较图模式、编译时间和图内存。

## 3. SGLang：缓存和router要一起理解

RadixAttention管理可复用前缀，连续batch调度请求，模型kernel负责实际执行，router将请求发往实例或PD两侧。这些职责分开，才方便定位“缓存没命中”和“引擎计算慢”。

在已按官方安装说明准备的配套环境中，单实例入口为：

```bash
python -m sglang.launch_server \
  --model-path /srv/models/example-model \
  --host 127.0.0.1 --port 30000
```

先核对`/v1/models`和正常、流式、取消请求。缓存测试采用稳定前缀、只改尾部问题；另设不同前缀对照，区分真正命中和普通进程预热。参数名字不能从vLLM直接搬过来；保存本版本`launch_server --help`。

需要PD时，接入官方router与NIXL/Mooncake，完整步骤见[分离式推理](../performance/disaggregated-serving.md)。单实例没有阶段干扰证据时，先调chunk大小和队列，避免过早增加架构复杂度。

## 4. TensorRT-LLM：当前入口不只是一套离线engine构建

旧教程常围绕“转换checkpoint → build engine → executor”讲解。当前官方quick start同时提供`trtllm-serve`和Python `LLM`入口，可直接从受支持的HF或ModelOpt制品启动；某些路线仍使用离线构建，必须按模型与backend区分。

在官方配套NVIDIA容器内，最小示例是：

```bash
trtllm-serve "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
```

官方也给出`nvidia/Qwen3-8B-FP8`等预量化示例，运行前先核对GPU和kernel支持。不要因为命令没有手动build步骤，就认为不存在编译、warm-up、workspace与图捕获成本。

比较TensorRT-LLM与vLLM时，不能一边使用NVFP4、另一边BF16，再将全部变化归因引擎。先相同制品做可比测试；如果格式无法统一，则报告两套完整部署方案的结果和各自质量。

## 5. llama.cpp：GGUF服务也已包含多种推测路径

当前源码文档包含draft、EAGLE-3、DFlash、DSpark和多种n-gram路线。它们的参数与转换条件不相同。`-md`只指定草稿文件，不能据此推断草稿算法；检查`--spec-type`以及相应模型支持。

DSpark当前文档限定Qwen3 backbone支持，其他模型制品能够转换并不等于server能运行。完整Qwen3-4B流程见[DSpark专题](../performance/dspark.md)。

同样，GGUF保存了量化类型，不自动保证每个平台都有高效kernel。CPU、CUDA、HIP、Vulkan、Metal上的同文件，卸载、KV、图实现与性能可能不同。

## 6. 当前模型结构对优化的影响

| 结构 | 改变什么 | 工程上要查什么 |
| --- | --- | --- |
| GQA/MQA | KV head少于query head | 按KV head估算状态与TP复制 |
| MLA | 压缩潜在状态及相应计算路径 | 专用缓存布局、attention和并行支持 |
| 滑动/稀疏attention | 部分层只访问窗口或选中的历史 | 实际缓存保留、索引成本、长文质量 |
| GDN/SSM等混合结构 | 部分层维护循环状态 | 状态checkpoint、分叉/回滚、推测与缓存兼容 |
| MoE | 每token只激活部分专家 | 总权重容量、路由、EP与all-to-all |
| 多模态 | processor/encoder增加输入与计算 | 图像/音频预算、缓存与接口 |

不能把纯attention的KV公式套到全部层，也不能强制所有层使用同一种attention backend。遇到混合层不支持时，检查引擎的逐层选择和架构支持。

## 7. 安装与升级时保存什么

保存宿主设备/驱动、CPU架构、镜像digest或wheel版本、PyTorch/CUDA/ROCm构建、扩展库、引擎commit和本地diff。开发文档出现的新参数，不意味着当前pip稳定版已经支持。

新版本至少通过：旧模型加载、短题、最长目标输入、SSE、取消、质量集、同负载三轮性能和持续运行。成功后再更新默认服务。遇到图或kernel错误，回到已验证组合定位，不把随机混装依赖作为长期修复。

## 8. 官方入口

- [vLLM优化文档固定快照](https://github.com/vllm-project/vllm/blob/2365177ddda7714502e4df7a1669cc79c0a4dfd0/docs/configuration/optimization.md)。
- [SGLang官方文档](https://docs.sglang.ai/)与[源码](https://github.com/sgl-project/sglang)。
- [TensorRT-LLM quick start](https://nvidia.github.io/TensorRT-LLM/quick-start-guide.html)。
- [llama.cpp推测解码固定快照](https://github.com/ggml-org/llama.cpp/blob/5aeac37a35b44fde4bdffaec9159f2fcb253b622/docs/speculative.md)。
