# 附录 B：参考资料与原稿修订

[总目录](../README.md) · [常用命令](commands.md) · [工程来源](../evidence/README.md)

## B.1 官方资料入口

官方文档用于核对支持条件与概念，性能数字使用作者工程记录。下列入口可能随上游变化；复现旧实验时，应继续查固定commit、release与对应文档。

| 主题 | 资料 | 阅读重点 |
| --- | --- | --- |
| llama.cpp | [源码与文档](https://github.com/ggml-org/llama.cpp) | 构建、模型架构、后端、server与量化 |
| llama.cpp构建 | [build.md](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md) | CMake变量、依赖与平台条件 |
| vLLM | [文档](https://docs.vllm.ai/) / [源码](https://github.com/vllm-project/vllm) | 安装平台、支持模型、调度、量化与benchmark |
| NVIDIA CUDA | [兼容性说明](https://docs.nvidia.com/deploy/cuda-compatibility/) | 驱动与Runtime关系 |
| NVIDIA架构 | [CUDA GPUs](https://developer.nvidia.com/cuda-gpus) | 精确GPU计算能力 |
| NVIDIA容器 | [Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/) | 宿主驱动、容器设备访问 |
| ROCm | [文档](https://rocm.docs.amd.com/) | 设备/系统矩阵、HIP、库与安装 |
| HIP | [文档](https://rocm.docs.amd.com/projects/HIP/en/latest/) | 编译目标与执行接口 |
| OpenVINO | [文档](https://docs.openvino.ai/) / [GenAI](https://github.com/openvinotoolkit/openvino.genai) | IR、设备插件、Pipeline、PerfMetrics |
| oneAPI | [开发工具](https://www.intel.com/content/www/us/en/developer/tools/oneapi/overview.html) | SYCL编译器与运行时 |
| MLX | [框架](https://github.com/ml-explore/mlx) / [MLX-LM](https://github.com/ml-explore/mlx-lm) | Apple执行与模型支持 |
| MLX视觉 | [MLX-VLM](https://github.com/Blaizzy/mlx-vlm) | 模型、processor与视觉生成 |
| 昇腾vLLM | [vllm-ascend](https://github.com/vllm-project/vllm-ascend) | 芯片、CANN、插件与vLLM版本配套 |
| ModelScope | [文档与SDK](https://github.com/modelscope/modelscope) | 模型下载、revision与制品 |
| EvalScope | [源码与文档](https://github.com/modelscope/evalscope) | 请求负载、指标与版本 |

这是一份参考入口清单，不表示本轮在所有平台重新验证了最新版本。

## B.2 原稿中需要修订的表达

| 原稿或旧笔记中的表达 | 本体系采用的说明 |
| --- | --- |
| GGUF归为一种量化算法 | GGUF是格式；其中可保存不同精度和量化类型 |
| Q4_K_M的K是k-means | K指K-quant家族；不按k-means解释 |
| AWQ/GPTQ/GGUF处于同一分类 | 分开记录格式、量化方法、位宽、布局与执行kernel |
| 低位宽一定快 | 需要匹配kernel、设备和负载，质量单独验收 |
| FP8转FP16恢复原精度 | 只改变表示，已损失信息不会自动恢复 |
| FP8模型就使用FP8 KV | 权重与KV是独立配置 |
| 模型参数×位宽就是全部显存 | 另算KV、激活、workspace、图、池与余量 |
| MoE只需加载激活参数 | 总权重仍需存储，卸载/分布式另有代价 |
| 双RTX4080可装NVLink桥 | RTX4080不支持NVLink，按实际PCIe拓扑验证 |
| 两卡显存可直接当一张大卡 | 框架切分、kernel、通信和资源预算需分别支持 |
| gpu-memory-utilization提高算力占用 | 这是引擎内存预算比例，不是GPU计算利用率目标 |
| 统一内存容量就是设备可分配容量 | 另有系统、驱动、运行时与应用预算 |
| 编译成功或设备枚举成功就是适配成功 | 还需目标模型、功能、长度、负载与质量验收 |
| Continuous Batching等于把并发设大 | 动态调度机制与配置的活动序列上限不同 |
| Prefix Cache会加速所有请求 | 需要满足前缀匹配、容量和实现条件 |
| 吞吐上升就是用户更快 | 同时看TTFT、ITL、E2E与尾延迟 |
| 引擎tg与HTTP吞吐直接相除 | 统一计时边界与负载后再比较 |
| 一条请求配置并发10就是十并发测试 | 看实际同时发出的请求与样本数 |
| 多参数方案收益归因单个开关 | 记录组合观察；因果判断需要控制变量 |

## B.3 原图怎样阅读？

作者提供的[原始框架图](../assets/edge-llm-deployment-framework-original.png)保留不改，作为知识范围参考。图中的分类和简写以本附录及正文的解释为准。

## B.4 来源与引用规则

概念与支持条件优先查对应官方文档；性能与故障引用作者具体工程记录。私人页面不公开，采用E01～E20编号和技术标题建立[来源索引](../evidence/README.md)。

正文将历史观察、命令模板、教学算例和待测事项区分描述。示例代码是公开路径改写；没有本轮硬件执行证据的地方，不写为本轮实测。

外部模型和数据以各自许可证为准，仓库文档许可不自动赋予模型再分发权限。没有取得公开权利的原图、样本与日志不转存。

## B.5 本次扩写的模型与实现资料

| 对应内容 | 公开资料入口 |
| --- | --- |
| OpenVINO Qwen3-TTS转换与运行 | [官方Notebook](https://github.com/openvinotoolkit/openvino_notebooks/blob/latest/notebooks/qwen3-tts/qwen3-tts.ipynb) |
| Kokoro OpenVINO/NPUW方法 | [官方Notebook](https://github.com/openvinotoolkit/openvino_notebooks/blob/latest/notebooks/kokoro/kokoro.ipynb) |
| Kokoro模型、许可与音色 | [模型卡](https://huggingface.co/hexgrad/Kokoro-82M) · [音色说明](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md) |
| BabelVox INT8模型与设备分工 | [模型卡](https://huggingface.co/djwarf/babelvox-openvino-int8) |
| Qwen3-TTS原模型与CPU成品来源 | [Qwen模型卡](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice) · [社区IR](https://huggingface.co/aurora2035/Qwen3-TTS-12Hz-0.6B-CustomVoice-OpenVINO-INT8) |
| MLX-VLM | [项目与模型支持说明](https://github.com/Blaizzy/mlx-vlm) |
| llama.cpp RPC | [RPC说明](https://github.com/ggml-org/llama.cpp/tree/master/tools/rpc) |
| Ray/vLLM多节点 | [vLLM分布式服务文档](https://docs.vllm.ai/en/latest/serving/distributed_serving/) |

以上latest/main/master链接用于继续查阅；正文实测仍按标明的历史日期与版本阅读。复现实验应把所用Notebook/代码也固定到具体commit，不能用今天的默认分支覆盖原来的支持条件。

## B.6 硬件与计算软件栈基础

这些资料用于理解组件职责；具体安装仍按目标硬件、OS和引擎的配套版本执行。

| 平台/主题 | 官方资料 | 核对内容 |
| --- | --- | --- |
| CUDA平台 | [CUDA Platform](https://docs.nvidia.com/cuda/cuda-programming-guide/01-introduction/cuda-platform.html) | 驱动、Driver API、Runtime与Toolkit的关系 |
| NVIDIA矩阵库 | [cuBLAS/cuBLASLt](https://docs.nvidia.com/cuda/cublas/index.html) | 矩阵计算、布局、数据类型与算法 |
| NVIDIA通信 | [NCCL](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/overview.html) | 集合通信与互联 |
| AMD平台 | [What is ROCm](https://rocm.docs.amd.com/en/latest/what-is-rocm.html) | 编译器、运行时、计算库与工具 |
| AMD设备支持 | [ROCm on Radeon/Ryzen](https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/) | 精确型号、OS和软件覆盖 |
| AMD通信 | [RCCL](https://rocm.docs.amd.com/projects/rccl/en/latest/) | 多GPU/多节点集合通信 |
| Apple GPU接口 | [Metal](https://developer.apple.com/metal/) | GPU命令、shader与计算执行 |
| Apple机器学习框架 | [MLX](https://ml-explore.github.io/mlx/build/html/index.html) / [统一内存](https://ml-explore.github.io/mlx/build/html/usage/unified_memory.html) | 数组、CPU/GPU、共享内存、惰性求值 |
| Apple文本模型 | [MLX-LM](https://github.com/ml-explore/mlx-lm) | 在MLX之上提供模型实现与生成工具 |
| Intel开发栈 | [oneAPI](https://www.intel.com/content/www/us/en/developer/tools/oneapi/overview.html) / [OpenVINO](https://docs.openvino.ai/) | 开发工具、计算库、推理Runtime与生成式管线 |
| 昇腾软件栈 | [CANN](https://www.hiascend.com/en/software/cann) | 运行时、算子、开发工具和上层配套 |

## 2026-10 工程更新

本轮官方资料、固定源码、概念修订和验证状态集中在[2026-10资料核查](../evidence/2026-10-refresh.md)。
