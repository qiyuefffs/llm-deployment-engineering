# 13 术语、材料来源与阅读索引

[总目录](README.md) · [上一章](12-delivery-and-learning.md)

本章用于查词和查证据。正文按操作过程学习，遇到陌生词再回这里，不需要先背完术语。

## 1. 模型与执行

| 词 | 简明解释 | 进入哪一步时需要 |
| --- | --- | --- |
| Token | 模型处理的文本单位，不等于字符 | 统计长度与速度 |
| Tokenizer | 文本与 token 的转换规则 | 准备模型与计算实际长度 |
| Chat template | 将角色和消息组织成模型输入 | 第一次对话和模板排查 |
| GGUF | 张量和元数据容器，可装不同精度 | llama.cpp 模型准备 |
| safetensors | 张量存储格式，通常还需其他配置文件 | HF 模型准备 |
| GPTQ/AWQ | 量化方法；还要匹配布局与 kernel | 选择量化制品 |
| W4A16 | 常见的权重/激活位宽描述 | 估算和核对精度路径 |
| Kernel | 在后端执行某种计算的实现 | 模型执行与性能排查 |
| Offload | 将部分或全部计算/权重放到另一设备 | 显存不足与设备迁移 |
| Fallback | 不支持或不满足条件时回到其他执行路径 | 判断为什么 GPU 没有按预期工作 |
| MoE | 按路由激活部分专家的模型 | 区分总权重容量与每步计算 |

## 2. 内存与调度

| 词 | 简明解释 | 实际检查 |
| --- | --- | --- |
| Prefill | 处理输入并建立生成状态 | 输入长度、时间与排队 |
| Decode | 在已有状态上继续生成 | 实际输出数与生成时间 |
| KV Cache | 常见注意力模型保存历史 K/V 的状态 | 架构、头数、精度、驻留 token |
| GQA | 多组 query 共享较少 KV 头 | KV 估算使用 KV 头数 |
| MLA/混合架构 | 缓存结构可能不同于普通完整 K/V | 看实际模型实现与日志 |
| Continuous batching | 在迭代边界加入、移除活跃序列 | 吞吐和单请求延迟一起测 |
| Chunked Prefill | 将输入计算分块参与调度 | 长短输入混跑时的等待 |
| Prefix caching | 复用符合条件的相同 token 前缀状态 | 命中、冷暖状态和支持范围 |
| Paged KV | 以块管理 KV 分配与访问 | 容量、共享、碎片和抢占 |
| Unified/共享内存 | 平台相关的 CPU/GPU 内存共享或管理方式 | 物理容量、运行时上限、系统可用量 |
| TP/PP/DP/EP | 张量、流水线、副本、专家并行 | 分什么、通信什么、目标是什么 |
| RPC | 通过远程调用使用另一进程/设备资源 | 连接、容量、传输与后端日志 |

## 3. 测量与交付

| 词 | 简明解释 | 需要写清的口径 |
| --- | --- | --- |
| TTFT | 请求到首有效输出的等待 | 客户端还是引擎、思考还是最终答案 |
| TPOT | 请求内首输出后的平均 token 时间 | 实际输出数和计算方式 |
| ITL | token 或工具定义的流式间隔 | 一次事件是否含多个 token |
| Throughput | 同一时间窗内的完成量 | 输出/总 token、时间窗、失败处理 |
| P95/P99 | 指定统计方法下的尾延迟 | 样本数和分位数算法 |
| SLO | 预先约定的服务目标 | 什么负载下达到什么门槛 |
| Goodput | 单位时间内满足约定条件的完成量 | 延迟、质量和成功规则 |
| Warmup | 正式测量前的预热 | 预热了哪些缓存和计算路径 |
| Readiness | 目标模型具备接收任务的条件 | 不能只看进程或端口 |
| Revision/digest/SHA256 | 锁定源码、模型或镜像身份的方法 | 不能只留可变名称 |

## 4. 本次从 FlowUs 提炼了哪些材料

先核对全空间目录与部署相关检索，再阅读相关目录页和正文，按具体流程选取实例。没有把空间内所有文章正文作为公开附件导出，也没有把读取页数等同于实测项目数。

下表列出正文实际采用的主要技术笔记。只保留可公开工程信息，不公开私人页面地址、账号、个人路径、内部地址和原始签名附件。完整映射与证据边界见[资料说明](evidence/README.md)。

| 技术笔记 | 主要用于 | 保留的判断边界 |
| --- | --- | --- |
| AMD 780M-GPU 适配教程、780M 配置与 890M 记录 | 02、06：识别设备、社区库与版本配套 | 不把下载链接当成成功测试 |
| ROCm 与 PyTorch 适配、AMD ROCm vLLM 编译 | 02、06、10：后端和编译目标 | 旧依赖和 SDK 条件按版本解释 |
| Linux CUDA、Flash Attention、CUDA/Vulkan 编译记录 | 02、05、10：工具链与构建 | 分开驱动、Toolkit、运行库 |
| 双 RTX 4080 vLLM Docker 部署记录 | 07、11：挂载和双卡配置 | 多变量历史速度不算严格优化收益 |
| DGX Spark Qwen3.6 BF16/FP8 编译部署 | 02、08、10：新架构和突发压力 | 只转录有输出的 FP8 测试 |
| DGX Spark Gemma4 开启/关闭 MTP、DFlash 编译与测试 | 09：推测解码条件与代价 | MTP 同看流式延迟；DFlash 多变量差异不作单项收益 |
| RTX 2060 Qwen3 Q6/Q5 混合推理记录 | 04、10：主机内存、交换、GPU 卸载 | 单次引擎速度不当作 API 压测 |
| Mac Metal 编译、vllm-metal、MLX/oMLX 记录 | 06、08、10：后端、模板和功能差异 | 限定版本；文本和视觉分别验收 |
| Qwen3.5-9B Intel OpenVINO 对比报告 | 03、06、09、10：制品、后端与失败 | 不混用 benchmark/API/管线计时 |
| AMD 395 五机 HIP RPC、编译与多节点排障 | 10、11：容量、运行时上限和通信 | 小上下文成功不替代大服务验收 |
| Prefill、Prefix Cache、KV Cache 学习记录 | 01、04、07 | 修正 vLLM APC 与 RadixAttention 的混用 |
| Conda/PyInstaller 打包记录 | 12 | 区分环境、客户端和引擎制品 |

## 5. 有哪些可以直接复查的公开产物

| 产物 | 位置 | 用途 |
| --- | --- | --- |
| 原始框架图 | [图片](assets/edge-llm-deployment-framework-original.png) | 对照原稿范围 |
| A10 实验截图、代码、输入、汇总 | [独立 Case](../../cases/llama-cpp-flash-attention/README.md) | 原有实测参考，目录保持独立 |
| 公开测试输入 | [workload.jsonl](../../cases/llama-cpp-flash-attention/data/workload.jsonl) | 8 条人工编写的公开技术问题 |
| A10 汇总 | [observed-summary.csv](../../cases/llama-cpp-flash-attention/results/observed-summary.csv) | 12 组历史转录 |
| FlowUs 技术测量转录 | [measurements.json](evidence/measurements.json) | Intel、DGX、oMLX、MTP、DFlash、RPC 主要数字 |
| 离线复查 | [脚本](examples/verify_records.py) · [本轮输出](examples/verified-output.txt) | 校验计数、哈希与计算，不运行模型 |
| 设备通信入口 | [all_reduce_check.py](examples/all_reduce_check.py) | 在准备好的双 GPU 环境执行；本轮未运行 |

原有 Case 的成功构建完整日志、全新实例重建和公开逐请求证据仍不齐备。本次公开转录也不能替代其他平台原始测试文件。它们适合用来讲解工程过程，不能被包装成所有平台都已经完成公开复现认证。

## 6. 对旧知识框架作了哪些修订

| 原稿容易误读的说法 | 本体系采用的表述 |
| --- | --- |
| GGUF、GPTQ、AWQ 都是同类格式 | 容器、精度、量化方法和执行布局分开 |
| vLLM 的 Prefix Cache 就是 RadixAttention | 区分 vLLM 哈希块复用与 SGLang 机制 |
| RTX 4080 可以加 NVLink 桥接器 | 该设备不支持 NVLink，检查实际 PCIe 拓扑 |
| nvidia-smi 的 CUDA 就是 nvcc 版本 | 驱动能力、Toolkit 与 wheel 构建分别核对 |
| 改 gfx/sm 就能获得完整硬件支持 | 编译目标只是兼容链中的一环 |
| GPU 满载说明已经优化好 | 以质量、延迟、吞吐和资源验收 |
| 模型总文件大小等于 MoE 每 token 读取量 | 区分总存储、激活计算与实际访存 |
| 编译成功/枚举成功等于模型可用 | 还要建图、执行和业务功能验收 |
| 可以用短生成结果验收完整答案 | 检查截断、思考模式和任务完成 |

原图原样保留，帮助对照最初的知识范围。正文与证据说明优先于图上的简写；图不是已验证硬件支持矩阵。

## 7. 官方资料按问题查阅

核对日期：2026-10-18。以下 `master/stable/latest` 入口会更新；复现实验以该实例记录的 commit、包版本、模型哈希和 `--help` 为准。

| 需要解决的问题 | 官方/原始资料 |
| --- | --- |
| llama.cpp 如何构建后端 | [build.md](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md) |
| HTTP 接口、槽位和参数 | [llama-server](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md) |
| 引擎 pp/tg 基准怎样测 | [llama-bench](https://github.com/ggml-org/llama.cpp/blob/master/tools/llama-bench/README.md) |
| RPC 构建与限制 | [llama.cpp RPC](https://github.com/ggml-org/llama.cpp/blob/master/tools/rpc/README.md) |
| vLLM 前缀缓存设计 | [Automatic Prefix Caching](https://docs.vllm.ai/en/stable/design/prefix_caching/) |
| vLLM 调度和内存 | [Optimization](https://docs.vllm.ai/en/stable/configuration/optimization/) · [Conserving memory](https://docs.vllm.ai/en/stable/configuration/conserving_memory/) |
| vLLM 模型量化条件 | [Quantization](https://docs.vllm.ai/en/stable/features/quantization/) |
| NVIDIA 驱动与工具链 | [CUDA Compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/) · [GPU 能力表](https://developer.nvidia.com/cuda-gpus) |
| RTX 4080 设备规格 | [NVIDIA 产品页](https://www.nvidia.com/en-us/geforce/graphics-cards/40-series/rtx-4080/) |
| AMD 芯片、系统和 ROCm | [ROCm 文档](https://rocm.docs.amd.com/en/latest/) |
| Intel OpenVINO 模型与管线 | [OpenVINO GenAI](https://github.com/openvinotoolkit/openvino.genai) |
| Apple MLX 模型与执行 | [MLX-LM](https://github.com/ml-explore/mlx-lm) · [MLX-VLM](https://github.com/Blaizzy/mlx-vlm) |
| 昇腾插件版本条件 | [vllm-ascend](https://github.com/vllm-project/vllm-ascend) |
| PyTorch 设备通信 | [Distributed](https://docs.pytorch.org/docs/stable/distributed.html) |
| Python 应用打包 | [PyInstaller](https://pyinstaller.org/en/stable/) |

论文可以帮助理解机制，但不会替你证明某设备和版本支持。FlashAttention 原理参考[论文](https://arxiv.org/abs/2205.14135)，PagedAttention 参考[论文](https://arxiv.org/abs/2309.06180)。实际性能仍用本机输入、参数和日志判断。
