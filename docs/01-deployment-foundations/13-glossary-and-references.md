# 13 术语、原图修订与参考资料

[返回总目录](README.md) · [上一章](12-delivery-and-learning.md)

## 1. 请求与调度术语

| 术语 | 工程解释 | 详见 |
| --- | --- | --- |
| Tokenizer | 将文本与模型 token 序列相互转换；版本影响长度和内容 | [01](01-engineering-and-request.md) |
| Chat template | 将角色、消息、工具与特殊 token 编排成模型输入 | [01](01-engineering-and-request.md) |
| Prefill | 处理输入并建立用于生成的状态；不等于全部 TTFT | [01](01-engineering-and-request.md) |
| Decode | 在已有状态上继续生成；单序列存在自回归依赖 | [01](01-engineering-and-request.md) |
| KV Cache | 常见 Attention 架构保存历史 Key/Value 的状态 | [04](04-memory-and-kv-cache.md) |
| Continuous batching | 在迭代边界动态加入和移除序列的调度方式 | [07](07-serving-and-scheduling.md) |
| Chunked Prefill | 将输入处理分块，与其他工作混合调度 | [07](07-serving-and-scheduling.md) |
| Prefix caching | 复用相同 token 前缀的状态；不是语义检索 | [07](07-serving-and-scheduling.md) |
| Paged KV / PagedAttention | 分块管理 KV 与相应访问计算；节省分配浪费 | [07](07-serving-and-scheduling.md) |
| Flash Attention | 优化 Attention 的计算/访存组织；不是权重量化 | [09](09-profiling-and-optimization.md) |
| CUDA Graph | 通过图捕获/回放减少部分运行期开销；有初始化与内存代价 | [07](07-serving-and-scheduling.md) |
| Speculative decoding | 先提出候选再批量验证，收益依赖成本与接受情况 | [09](09-profiling-and-optimization.md) |

## 2. 架构、表示与硬件术语

| 术语 | 工程解释 | 详见 |
| --- | --- | --- |
| MHA/GQA/MQA | 多头/分组查询/多查询 Attention；KV 头数不同 | [04](04-memory-and-kv-cache.md) |
| MLA | 潜在状态压缩相关 Attention 架构；不能照搬普通 KV 公式 | [04](04-memory-and-kv-cache.md) |
| MoE | 按路由激活部分专家；总权重与激活计算量是两个概念 | [11](11-parallel-and-scaling.md) |
| GGUF | 张量与元数据容器，可包含多种精度/量化类型 | [03](03-model-and-quantization.md) |
| safetensors | 张量序列化格式；不单独描述整个执行环境 | [03](03-model-and-quantization.md) |
| AWQ/GPTQ | 量化方法；部署还涉及打包、配置与 kernel | [03](03-model-and-quantization.md) |
| W4A16 | 常见的权重/激活位宽描述；不是完整的量化规范 | [03](03-model-and-quantization.md) |
| Kernel | 后端执行某类计算的实现；支持和效率依硬件、shape、精度 | [02](02-hardware-compatibility.md) |
| Offload / fallback | 计划性卸载与不支持路径回退，需看实际数据流 | [04](04-memory-and-kv-cache.md) |
| Unified memory | 平台相关的共享/管理机制；不意味着容量可重复相加 | [04](04-memory-and-kv-cache.md) |
| NUMA | CPU/内存访问具有局部性；跨节点访问有额外成本 | [09](09-profiling-and-optimization.md) |
| TP/PP/DP/EP | 张量、流水线、数据/副本、专家并行 | [11](11-parallel-and-scaling.md) |

## 3. 测量与交付术语

| 术语 | 工程解释 | 详见 |
| --- | --- | --- |
| TTFT | 请求到首个有效输出的等待，需定义观察位置 | [08](08-benchmark-and-quality.md) |
| TPOT | 请求内首输出后的平均 token 时间，依赖实际输出数 | [08](08-benchmark-and-quality.md) |
| ITL | 连续 token 的间隔；客户端片段间隔可能只是近似观测 | [08](08-benchmark-and-quality.md) |
| Throughput | 统一时间窗内的完成量，不是单请求速率之和 | [08](08-benchmark-and-quality.md) |
| SLO / Goodput | 预定服务目标 / 单位时间内满足约定条件的请求数 | [08](08-benchmark-and-quality.md) |
| Cold / warm | 冷暖状态可能涉及模型、页、编译、前缀等不同缓存 | [07](07-serving-and-scheduling.md) |
| Revision / digest | 追踪源码、模型或镜像身份，减少可变名称歧义 | [12](12-delivery-and-learning.md) |
| Readiness | 目标模型已具备接收任务条件，与进程存活不同 | [12](12-delivery-and-learning.md) |

## 4. 原稿和框架图的修订原则

保留原有五层能力、七模块与“需求—设计—部署—压测—排障—迭代”闭环；原图完整保留在 [assets](assets/edge-llm-deployment-framework-original.png)，没有将它修改成新的实测证明图。

正文做了以下技术修订：将文件容器、数值精度、量化方法、编译图分开；将框架选型改为依工作负载验证；KV 计算使用实际 KV 头和架构；TPOT 与 ITL 分别定义；引擎 bench 与 HTTP 指标分开；补充质量、Goodput、温控和能耗；对新后端和插件按版本限定。

尤其不延续这些绝对结论：“INT4 一定快”“GPU utilization 高就是性能好”“模型已加载就不会 OOM”“图中列出某后端就支持所有模型”“TP 多一倍就快一倍”。相关原理与反例已在各章展开。

原图中的 OpenVINO、FP8/INT4、GGUF、vLLM 等文字要按修订后的分类阅读。当前 llama.cpp 主线已有 OpenVINO 等新后端，旧版安装指南或旧 commit 未必包含它。不要把过去的“没有”或现在的“有”扩大成永久结论。

## 5. 官方资料入口与阅读目的

以下来源用于核对概念、构建和支持边界。核对日期 **2026-10-17**。`master`、`stable`、`latest` 是可变入口；真正复现实验时须保存实际 commit、版本和当时的 `--help`。表中链接不是一张已逐项完成硬件测试的清单。

| 主题 | 官方/原始来源 | 重点阅读 |
| --- | --- | --- |
| llama.cpp | [主仓库](https://github.com/ggml-org/llama.cpp) | 架构、工具、后端与发布记录 |
| 构建 | [build.md](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md) | CMake、CPU/CUDA/Metal、后端前提 |
| HTTP 服务 | [server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md) | 槽位、上下文、API、模板、metrics |
| 引擎压测 | [llama-bench README](https://github.com/ggml-org/llama.cpp/blob/master/tools/llama-bench/README.md) | pp/tg、组合/深度测试、参数和输出格式 |
| Android | [Android 文档](https://github.com/ggml-org/llama.cpp/blob/master/docs/android.md) | ABI、NDK、Termux 与应用入口 |
| Intel SYCL | [SYCL.md](https://github.com/ggml-org/llama.cpp/blob/master/docs/backend/SYCL.md) | oneAPI/驱动、构建和设备要求 |
| OpenVINO 后端 | [OPENVINO.md](https://github.com/ggml-org/llama.cpp/blob/master/docs/backend/OPENVINO.md) | 所选版本支持与部署限制 |
| 推测解码 | [llama.cpp speculative](https://github.com/ggml-org/llama.cpp/blob/master/docs/speculative.md) | 草稿机制、实现条件与参数 |
| vLLM 安装 | [安装与硬件入口](https://docs.vllm.ai/en/stable/getting_started/installation/) | OS/设备、预编译包与插件 |
| vLLM 调优 | [Optimization and Tuning](https://docs.vllm.ai/en/stable/configuration/optimization/) | 调度、抢占、分块与并行 |
| vLLM 内存 | [Conserving Memory](https://docs.vllm.ai/en/stable/configuration/conserving_memory/) | 上下文、执行配置和内存来源 |
| vLLM 量化 | [Quantization](https://docs.vllm.ai/en/stable/features/quantization/) | 硬件/方法矩阵与限制 |
| vLLM 工具 | [vLLM 源码](https://github.com/vllm-project/vllm) | 版本相关 CLI、benchmark 和测量实现 |
| Ascend 插件 | [vllm-ascend](https://github.com/vllm-project/vllm-ascend) | 插件版本、模型/芯片支持 |
| SGLang | [官方文档](https://docs.sglang.io/) | 缓存、结构化输出、并行与分离式 serving |
| TensorRT-LLM | [官方仓库](https://github.com/NVIDIA/TensorRT-LLM) | 模型/硬件、运行路线与构建 |
| MLX-LM | [官方仓库](https://github.com/ml-explore/mlx-lm) | Apple 模型加载、转换、量化与生成 |
| Intel NPU | [OpenVINO GenAI on NPU（2025 文档）](https://docs.openvino.ai/2025/openvino-workflow-generative/inference-with-genai/inference-with-genai-on-npu.html) | 版本内的导出、量化、代际和形状限制 |
| NVIDIA 工具链 | [CUDA Linux 安装指南](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/)、[CUDA Compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/) | 驱动/Toolkit/Runtime 的关系 |
| GPU 架构 | [CUDA GPU 能力表](https://developer.nvidia.com/cuda-gpus) | 精确设备的 Compute Capability |
| AMD | [ROCm 文档](https://rocm.docs.amd.com/en/latest/) | GPU/OS 兼容与版本组合 |
| Android 工具链 | [NDK 与 CMake](https://developer.android.com/ndk/guides/cmake) | 跨编译、ABI 与原生库 |
| Metal | [Apple Metal](https://developer.apple.com/metal/) | GPU API 与平台资料 |
| 性能时间线 | [Nsight Systems Guide](https://docs.nvidia.com/nsight-systems/UserGuide/index.html) | CPU/GPU/复制/同步时间线 |

OpenVINO NPU 一行特意使用版本化文档，说明约束具有版本性；不把该页中的包版本或默认形状宣称为所有新版本的要求。其他厂商也应从对应设备/SDK 发布说明核对。

## 6. 论文用于理解机制，不替代版本支持表

| 机制 | 原始论文 | 阅读时关注 |
| --- | --- | --- |
| PagedAttention | [Efficient Memory Management for Large Language Model Serving](https://arxiv.org/abs/2309.06180) | KV 分块、共享与空间利用 |
| FlashAttention | [FlashAttention](https://arxiv.org/abs/2205.14135) | I/O-aware Attention 的工作方式 |
| GPTQ | [GPTQ](https://arxiv.org/abs/2210.17323) | 量化近似、校准与误差处理 |
| AWQ | [AWQ](https://arxiv.org/abs/2306.00978) | 激活感知权重量化的动机 |

论文中的特定硬件性能和当前框架默认行为不是同一件事。实现经过演进后可能使用不同 kernel、调度或约束，部署需要重新核对。

## 7. 材料性质与证据边界

本知识体系基于作者原稿、框架图、当前仓库实践背景与官方资料整理。原图是概念图；命令是模板；带“假设/理论”的数字是演算。它们都不是新硬件实测结果。

仓库 Case 保留独立的执行文件、结果与证据状态；知识章节不改写 Case 的实验结论。本次知识体系更新发布在作者个人仓库。后续补充新设备时，先填[适配记录](templates/adaptation-record.md)和[实验记录](templates/experiment-record.md)，有日志再将“待测”更新为验证结论。
