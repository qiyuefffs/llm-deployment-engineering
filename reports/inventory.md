# 章节盘点

本报告由 `python tools/inventory.py --write` 生成。字符数不包含空白，代码与正文分别统计；
`source_ids` 从正文中实际出现的 R/E 编号提取，不用章节标题推断。

## 总量

- Markdown 文档：140
- 正文字符：417,541
- 代码字符：266,070
- 代码块：1,294
- 唯一来源编号：82

## book

| 文件 | ID | 标题 | 正文字符 | 代码字符 | 代码占比 | 来源 |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `00-preface.md` | T00 | 工程资料约定与执行基线 | 1,057 | 198 | 15.8% | - |
| `01-knowledge-map.md` | T01 | 第一部分：整体知识体系地图 | 2,234 | 589 | 20.9% | - |
| `02-capability-layers/01-hardware-backends.md` | T02 | 第1层：硬件、运行时与计算后端 | 4,981 | 686 | 12.1% | - |
| `02-capability-layers/02-model-formats-quantization.md` | T03 | 第2层：模型格式与量化层 | 3,097 | 832 | 21.2% | - |
| `02-capability-layers/03-inference-frameworks.md` | T04 | 第3层：推理框架层 | 3,072 | 1,496 | 32.8% | - |
| `02-capability-layers/04-memory-performance.md` | T05 | 第4层：显存与性能优化层 | 3,775 | 269 | 6.7% | - |
| `02-capability-layers/05-engineering-delivery.md` | T06 | 第5层：工程交付层 | 2,067 | 163 | 7.3% | - |
| `02-capability-layers/README.md` | T07 | 第二部分：五层能力详细框架 | 867 | 68 | 7.3% | - |
| `03-core-concepts.md` | T08 | 第三部分：核心概念解释库 | 5,155 | 50 | 1.0% | - |
| `04-project-review.md` | T09 | 第四部分：项目复盘模板 | 3,986 | 273 | 6.4% | E02 |
| `05-knowledge-base.md` | T10 | 第五部分：个人知识库目录设计 | 3,115 | 146 | 4.5% | - |
| `06-troubleshooting.md` | T11 | 第六部分：故障排查速查表 | 3,100 | 234 | 7.0% | E01, E02, E03, E05, E10 |
| `README.md` | T12 | 大模型部署知识体系 | 5,236 | 483 | 8.5% | E01, E20, R01, R50 |
| `SUMMARY.md` | T13 | 大模型部署知识体系目录 | 7,731 | 0 | 0.0% | E01, E20, E21, E22, E23, E24, E25, E26, E27, E28, E29, E30, E31, E32, R01, R02, R03, R04, R05, R06, R07, R08, R09, R10, R11, R12, R13, R14, R15, R16, R17, R18, R19, R20, R21, R22, R23, R24, R25, R26, R27, R28, R29, R30, R31, R32, R33, R34, R35, R36, R37, R38, R39, R40, R41, R42, R43, R44, R45, R46, R47, R48, R49, R50 |
| `appendices/benchmark-tools.md` | T14 | 压测工具工程记录：llama-bench、vLLM bench与EvalScope | 744 | 0 | 0.0% | R48, R49 |
| `appendices/commands.md` | T15 | 附录 A：常用命令速查 | 1,386 | 1,808 | 56.6% | - |
| `appendices/gguf-ollama.md` | T16 | 模型制品工程记录：HF转换GGUF、量化与Ollama导入 | 485 | 96 | 16.5% | R50 |
| `appendices/references.md` | T17 | 附录 B：参考资料与原稿修订 | 5,035 | 0 | 0.0% | - |
| `assets/README.md` | T18 | 知识体系图片 | 822 | 0 | 0.0% | - |
| `chapters/delivery/api-monitoring.md` | T19 | API、监控与验收：让服务的状态可见 | 3,852 | 617 | 13.8% | - |
| `chapters/delivery/environment-operations.md` | T20 | 环境封装、启停与回滚 | 4,500 | 1,364 | 23.3% | - |
| `chapters/frameworks/llama-cpp.md` | T21 | llama.cpp：构建、加载、接口与停止 | 2,004 | 1,861 | 48.1% | - |
| `chapters/frameworks/openvino.md` | T22 | OpenVINO：用固定 IR 完成 Intel GPU 推理 | 7,197 | 3,545 | 33.0% | - |
| `chapters/frameworks/serving-engines.md` | T23 | 当前推理引擎怎么选：先匹配执行路径，再比较服务结果 | 3,323 | 461 | 12.2% | - |
| `chapters/frameworks/vllm-service.md` | T24 | vLLM：从模型目录到可测量的推理服务 | 5,137 | 2,978 | 36.7% | - |
| `chapters/hardware/amd.md` | T25 | 1.2.2 AMD GPU与ROCm软件栈 | 7,378 | 2,450 | 24.9% | - |
| `chapters/hardware/apple.md` | T26 | 1.2.4 Mac硬件、Metal与MLX | 7,648 | 2,774 | 26.6% | - |
| `chapters/hardware/ascend.md` | T27 | 1.2.5 昇腾：芯片、CANN与框架插件 | 2,173 | 358 | 14.1% | - |
| `chapters/hardware/dgx-spark.md` | T28 | DGX Spark / GB10：ARM64、统一内存与低位宽推理 | 2,466 | 338 | 12.0% | - |
| `chapters/hardware/intel.md` | T29 | 1.2.3 Intel硬件、oneAPI与OpenVINO | 5,239 | 1,150 | 18.0% | - |
| `chapters/hardware/nvidia.md` | T30 | 1.2.1 NVIDIA GPU与CUDA软件栈 | 6,726 | 1,301 | 16.2% | - |
| `chapters/models/gguf-conversion.md` | T31 | 从原始权重到可加载的 GGUF | 3,974 | 2,551 | 39.1% | - |
| `chapters/models/quantization.md` | T32 | 量化选择：从放得下到用得好 | 9,018 | 3,420 | 27.5% | - |
| `chapters/performance/benchmarking.md` | T33 | 性能测试：把一次运行变成可比较的结果 | 7,147 | 1,959 | 21.5% | - |
| `chapters/performance/cache-scheduling.md` | T34 | KV、缓存与调度：分别解决什么问题 | 6,586 | 1,663 | 20.2% | R42, R43 |
| `chapters/performance/disaggregated-serving.md` | T35 | 分离式推理：PD分离、KV传输与MoE并行 | 3,216 | 1,481 | 31.5% | - |
| `chapters/performance/dspark.md` | T36 | DSpark：从块草稿到自适应验证 | 5,700 | 2,717 | 32.3% | - |
| `chapters/performance/parallelism.md` | T37 | 多卡与多节点：先解决容量，再验证通信和收益 | 4,419 | 843 | 16.0% | - |
| `chapters/performance/speculative-decoding.md` | T38 | 推测解码：MTP、EAGLE、DFlash与DSpark | 7,178 | 2,063 | 22.3% | - |
| `engineering/README.md` | T39 | 硬件部署适配与加速优化实例索引 | 2,686 | 72 | 2.6% | - |
| `engineering/edge-llm-performance-methodology.md` | T40 | 通用性能优化测试方法论 | 7,314 | 144 | 1.9% | E25, E26, E28, E29 |
| `engineering/projects/01-minimax-m27.md` | T41 | MiniMax-M2.7 多机推理 | 4,532 | 852 | 15.8% | E21, E22 |
| `engineering/projects/02-deepseek-v4-flash.md` | T42 | DeepSeek V4 Flash 部署与推理性能优化 | 6,088 | 6,642 | 52.2% | E29 |
| `engineering/projects/03-qwen36-35b-a3b.md` | T43 | Qwen3.6-35B-A3B 部署与推理性能优化 | 5,404 | 5,727 | 51.4% | - |
| `engineering/projects/04-qwen38-27b-flash-next.md` | T44 | Qwen3.8-27B 与 Qwen3.8 Flash-Next 部署与推理性能优化 | 8,345 | 6,970 | 45.5% | - |
| `engineering/projects/05-glm-53-flash.md` | T45 | GLM-5.3-Flash 部署与推理性能优化 | 3,439 | 457 | 11.7% | E23, E24 |
| `engineering/projects/06-vllm-rocm.md` | T46 | vLLM ROCm 文本与多模态部署 | 5,607 | 591 | 9.5% | E25, E26, E27, E28, E29 |
| `engineering/projects/07-minimax-h3.md` | T47 | MiniMax-H3 视频/音频生成部署 | 4,523 | 426 | 8.6% | E30 |
| `engineering/projects/08-qwen-image-21.md` | T48 | Qwen-Image 2.1 图像生成部署 | 4,516 | 1,145 | 20.2% | E31, E32 |
| `engineering/projects/README.md` | T49 | 端侧模型项目文档索引 | 1,455 | 0 | 0.0% | E21, E32 |
| `templates/adaptation-record.md` | T50 | 端侧模型适配记录模板 | 891 | 0 | 0.0% | - |
| `templates/deployment-review.md` | T51 | 部署项目复盘模板 | 944 | 0 | 0.0% | - |
| `templates/experiment-record.md` | T52 | 推理优化实验记录模板 | 831 | 0 | 0.0% | - |

## cases

| 文件 | ID | 标题 | 正文字符 | 代码字符 | 代码占比 | 来源 |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `cases/C01-rtx2060/README.md` | C01 | NVIDIA RTX 2060 12GB：CUDA混合卸载与Qwen3量化推理 | 2,439 | 388 | 13.7% | R01, R02, R03 |
| `cases/C02-dual-4080/README.md` | C02 | NVIDIA RTX 4080与A6000：双卡vLLM部署和调参记录 | 2,188 | 345 | 13.6% | R04 |
| `cases/C03-gb10/README.md` | C03 | NVIDIA GB10：ARM64构建、FP8、AWQ、MTP与DFlash | 2,818 | 812 | 22.4% | R05, R06, R07, R08, R09, R10, R11, R12 |
| `cases/C04-gb10-multimodal/README.md` | C04 | NVIDIA GB10多模态：VL、Omni与文档模型的部署链路 | 2,024 | 446 | 18.1% | R13, R14, R15, R16, R17 |
| `cases/C05-radeon-780m/README.md` | C05 | AMD Radeon 780M：Windows HIP运行库、Ollama与模型适配 | 2,028 | 41 | 2.0% | R18, R19, R20 |
| `cases/C06-radeon-8060s/README.md` | C06 | AMD Radeon 8060S：Vulkan全层卸载、Q4与BF16优化对照 | 2,676 | 305 | 10.2% | R21, R22 |
| `cases/C07-amd-395-rpc/README.md` | C07 | AMD 395五机HIP RPC：GTT修复、构建、分发与Kimi加载 | 2,125 | 361 | 14.5% | R23, R24, R25 |
| `cases/C08-w7900/README.md` | C08 | AMD W7900：单机多卡、双节点Ray与TP/PP部署 | 2,441 | 304 | 11.1% | R26, R27, R28, R29, R30, R31, R32, R33, R34 |
| `cases/C09-intel-arc-npu/README.md` | C09 | Intel Arc与NPU：Vulkan、SYCL、IR和语音任务完整对照 | 2,438 | 573 | 19.0% | R35, R36, R37, R38 |
| `cases/C10-m3-metal/README.md` | C10 | Apple M3 Ultra：Metal工具链、GGUF适配与模型加载排错 | 1,841 | 320 | 14.8% | R39 |
| `cases/C11-m3-mlx/README.md` | C11 | Apple M3 Ultra：vllm-metal、MLX-VLM、APC与oMLX优化 | 2,291 | 664 | 22.5% | R40, R41, R42, R43, R44 |
| `cases/C12-ascend-310p/README.md` | C12 | 昇腾310P3：CANN容器、Qwen3部署与性能验收 | 2,053 | 559 | 21.4% | R45, R46, R47 |
| `cases/C13-musa/README.md` | C13 | MUSA：llama.cpp部署适配与加速验证流程 | 1,701 | 1,100 | 39.3% | - |
| `cases/C14-windows-cpu/README.md` | C14 | 完整操作实例：第一个本地推理服务 | 4,702 | 1,385 | 22.8% | - |
| `cases/README.md` | C00 | 实例卷索引 | 1,321 | 0 | 0.0% | R01, R02, R03, R04, R05, R06, R07, R08, R09, R10, R11, R12, R13, R14, R15, R16, R17, R18, R19, R20, R21, R22, R23, R24, R25, R26, R27, R28, R29, R30, R31, R32, R33, R34, R35, R36, R37, R38, R39, R40, R41, R42, R43, R44, R45, R46, R47 |

## evidence

| 文件 | ID | 标题 | 正文字符 | 代码字符 | 代码占比 | 来源 |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `evidence/2026-10-refresh.md` | EV02 | 2026-10部署与推理优化更新 | 4,636 | 0 | 0.0% | - |
| `evidence/README.md` | EV00 | 证据卷阅读说明 | 359 | 0 | 0.0% | E01, E20, E21, E32, R01, R50 |
| `evidence/chapter-sources.md` | EV01 | FlowUs 文章与章节对应表 | 6,131 | 0 | 0.0% | R01, R02, R03, R04, R05, R06, R07, R08, R09, R10, R11, R12, R13, R14, R15, R16, R17, R18, R19, R20, R21, R22, R23, R24, R25, R26, R27, R28, R29, R30, R31, R32, R33, R34, R35, R36, R37, R38, R39, R40, R41, R42, R43, R44, R45, R46, R47, R48, R49, R50 |
| `evidence/records/E21.md` | E21 | E21 · MiniMax 双机服务快照 | 1,311 | 3,572 | 73.2% | E21 |
| `evidence/records/E22.md` | E22 | E22 · MiniMax 双机部署与 API 验收 | 1,991 | 6,550 | 76.7% | E22 |
| `evidence/records/E23.md` | E23 | E23 · GLM BALANCED 随制品说明 | 7,934 | 216 | 2.6% | E23 |
| `evidence/records/E24.md` | E24 | E24 · GLM HYBRID 随制品说明 | 4,328 | 241 | 5.3% | E24 |
| `evidence/records/E25.md` | E25 | E25 · vLLM ROCm 部署方案 | 3,211 | 925 | 22.4% | E25 |
| `evidence/records/E26.md` | E26 | E26 · vLLM ROCm 基准测试口径 | 2,642 | 121 | 4.4% | E26 |
| `evidence/records/E27.md` | E27 | E27 · Qwen3-VL-4B Flash 对照结果 | 2,782 | 0 | 0.0% | E27 |
| `evidence/records/E28.md` | E28 | E28 · DeepSeek-VL2-Tiny 成功与失败结果 | 2,329 | 0 | 0.0% | E28 |
| `evidence/records/E29.md` | E29 | E29 · DeepSeek W4A16 TP1 与 TP2 对照 | 4,771 | 145 | 2.9% | E29 |
| `evidence/records/E30.md` | E30 | E30 · MiniMax-H3 视频音频实验记录 | 3,113 | 2,065 | 39.9% | E30 |
| `evidence/records/E31.md` | E31 | E31 · Qwen-Image 工程部署记录 | 3,415 | 898 | 20.8% | E31 |
| `evidence/records/E32.md` | E32 | E32 · Qwen-Image 故障复现与验收记录 | 6,058 | 2,154 | 26.2% | E32 |
| `evidence/records/README.md` | E00 | 工程来源与实测转录 | 5,589 | 73 | 1.3% | E01, E02, E03, E04, E05, E06, E07, E08, E09, E10, E11, E12, E13, E14, E15, E16, E17, E18, E19, E20 |
| `evidence/records/projects.md` | EV07 | 端侧项目补充证据索引 | 1,154 | 0 | 0.0% | E21, E22, E23, E24, E25, E26, E27, E28, E29, E30, E31, E32 |
| `evidence/sources/R01.md` | R01 | R01 · nvidai-llamacpp-qwen3:30-a3b-q6测试记录 | 855 | 174 | 16.9% | R01 |
| `evidence/sources/R02.md` | R02 | R02 · nvidai-llamacpp-qwen3:30-a3b-q6基准性能测试记录 | 394 | 262 | 39.9% | R02 |
| `evidence/sources/R03.md` | R03 | R03 · nvidai-llamacpp-qwen3:32B-q5基准性能测试记录 | 407 | 273 | 40.2% | R03 |
| `evidence/sources/R04.md` | R04 | R04 · 服务器：Nvidia显卡：Ubuntu22.04+VLLM+Docker双卡部署Deepseek-r1:32B(Int4) | 1,943 | 3,922 | 66.9% | R04 |
| `evidence/sources/R05.md` | R05 | R05 · NVIDIA GB10 ARM编译llamacpp | 117 | 1,570 | 93.1% | R05 |
| `evidence/sources/R06.md` | R06 | R06 · nvidia GB10设备（arm64架构）编译vllm | 201 | 1,863 | 90.3% | R06 |
| `evidence/sources/R07.md` | R07 | R07 · DGX Spark适配编译vllm部署Qwen3.6-35B-A3B模型（bf16/fp8精度） | 210 | 3,002 | 93.5% | R07 |
| `evidence/sources/R08.md` | R08 | R08 · NVIDIA GB10部署Qwen3-30B-A3B-Instruct-2507 | 99 | 2,746 | 96.5% | R08 |
| `evidence/sources/R09.md` | R09 | R09 · DGX GB10部署Gemma-4系列AWQ量化模型 | 277 | 7,273 | 96.3% | R09 |
| `evidence/sources/R10.md` | R10 | R10 · DGX Spark GB10部署gemma-4系列模型及关闭MTP推理加速 | 98 | 3,605 | 97.4% | R10 |
| `evidence/sources/R11.md` | R11 | R11 · DGX Spark GB10部署gemma-4系列模型及MTP推理加速 | 91 | 4,053 | 97.8% | R11 |
| `evidence/sources/R12.md` | R12 | R12 · DGX Spark GB10编译DFlash推理加速模块集成到vllm中 | 5,282 | 6,177 | 53.9% | R12 |
| `evidence/sources/R13.md` | R13 | R13 · GB10部署Qwen3-VL-8B模型 | 24 | 2,083 | 98.9% | R13 |
| `evidence/sources/R14.md` | R14 | R14 · nvidia GB10 部署Qwen2.5-VL-7B | 154 | 3,612 | 95.9% | R14 |
| `evidence/sources/R15.md` | R15 | R15 · GB10部署Qwen3-VL-30B-A3B | 27 | 728 | 96.4% | R15 |
| `evidence/sources/R16.md` | R16 | R16 · NVIDIA GB10版本vllm部署Qwen3‑Omni‑30B‑A3B‑Instruct | 64 | 1,151 | 94.7% | R16 |
| `evidence/sources/R17.md` | R17 | R17 · NVIDIA GB10 vllm部署granite-docling-258M | 41 | 674 | 94.3% | R17 |
| `evidence/sources/R18.md` | R18 | R18 · AMD 780M-GPU 适配教程 | 1,037 | 0 | 0.0% | R18 |
| `evidence/sources/R19.md` | R19 | R19 · AMD适配模型（GPU-780M，ＣＰＵ　－8845HS） | 633 | 7,448 | 92.2% | R19 |
| `evidence/sources/R20.md` | R20 | R20 · AMD：使用Ollama框架将Llama3.1 8b部署在AMD的GPU | 473 | 1,222 | 72.1% | R20 |
| `evidence/sources/R21.md` | R21 | R21 · Qwen3.6-35B-A3B 部署与推理文档 | 3,253 | 1,677 | 34.0% | R21 |
| `evidence/sources/R22.md` | R22 | R22 · Qwen3.6-35B-A3B BF16 推理优化记录 | 2,030 | 1,117 | 35.5% | R22 |
| `evidence/sources/R23.md` | R23 | R23 · AMD Strix Halo 395 五机 HIP RPC 串联部署 Kimi-K2.5-Q2 实战文档 | 4,964 | 11,977 | 70.7% | R23 |
| `evidence/sources/R24.md` | R24 | R24 · AMD 395 llamcpp+rpc编译流程 | 2,838 | 2,764 | 49.3% | R24 |
| `evidence/sources/R25.md` | R25 | R25 · AMD 395 llamacpp rpc服务功能环境测试脚本 | 70 | 9,312 | 99.2% | R25 |
| `evidence/sources/R26.md` | R26 | R26 · 单节点八卡服务器（W7900*8,48*8）DeepSeek-R1-AWQ-INT4部署 | 257 | 1,426 | 84.7% | R26 |
| `evidence/sources/R27.md` | R27 | R27 · W7900双卡部署Qwen3:30b-A3b | 1,844 | 961 | 34.3% | R27 |
| `evidence/sources/R28.md` | R28 | R28 · 服务器：AMD显卡：Ubuntu22.04+VLLM+Docker双卡部署Deepseek-r1:32b/70b | 2,262 | 4,890 | 68.4% | R28 |
| `evidence/sources/R29.md` | R29 | R29 · AMD单节点四卡DS-70B-fp16测试命令 | 55 | 4,570 | 98.8% | R29 |
| `evidence/sources/R30.md` | R30 | R30 · 双节点模型部署70B验证 | 1,162 | 4,053 | 77.7% | R30 |
| `evidence/sources/R31.md` | R31 | R31 · 双节点模型部署70B-2.0资源调度验证 | 1,170 | 3,959 | 77.2% | R31 |
| `evidence/sources/R32.md` | R32 | R32 · 双节点，再次推理DS-70B | 772 | 1,855 | 70.6% | R32 |
| `evidence/sources/R33.md` | R33 | R33 · Deepseek-R1-671b双节点部署 | 83 | 1,086 | 92.9% | R33 |
| `evidence/sources/R34.md` | R34 | R34 · 多节点部署排障 | 1,867 | 3,474 | 65.0% | R34 |
| `evidence/sources/R35.md` | R35 | R35 · Qwen3.5-9B Intel openvino 平台推理对比报告 | 15,086 | 5,958 | 28.3% | R35 |
| `evidence/sources/R36.md` | R36 | R36 · Qwen3.5-9B INT4 IR 多模态视觉推理测试报告 | 3,316 | 0 | 0.0% | R36 |
| `evidence/sources/R37.md` | R37 | R37 · 使用ipex-llm进行量化并制作ollama模型，部署在Intel集显。 | 816 | 671 | 45.1% | R37 |
| `evidence/sources/R38.md` | R38 | R38 · Intel NPU进行模型推理：deepseek-r1:1.5b,7b,8b | 378 | 1,474 | 79.6% | R38 |
| `evidence/sources/R39.md` | R39 | R39 · llama.cpp 在 Mac Studio (Apple Silicon) 上的编译指南 | 8,752 | 6,213 | 41.5% | R39 |
| `evidence/sources/R40.md` | R40 | R40 · vllm-metal 编译与推理记录 | 2,689 | 7,581 | 73.8% | R40 |
| `evidence/sources/R41.md` | R41 | R41 · mlx-vlm 多视觉模型推理与 API 调用指南 | 2,665 | 10,747 | 80.1% | R41 |
| `evidence/sources/R42.md` | R42 | R42 · oMLX Mac 推理操作流程 | 1,084 | 5,290 | 83.0% | R42 |
| `evidence/sources/R43.md` | R43 | R43 · oMLX 推理框架性能测试报告与压测流程 | 1,050 | 863 | 45.1% | R43 |
| `evidence/sources/R44.md` | R44 | R44 · Mac 设备推理框架分类总结 | 13,945 | 9,320 | 40.1% | R44 |
| `evidence/sources/R45.md` | R45 | R45 · 华为昇腾310P3推理Qwen3-32B | 174 | 1,598 | 90.2% | R45 |
| `evidence/sources/R46.md` | R46 | R46 · 华为昇腾310p3：qwen3-32b与qwen3-235b-a22b-2507测试 | 135 | 6,778 | 98.0% | R46 |
| `evidence/sources/R47.md` | R47 | R47 · 昇腾310P3部署Qwen3-32B benchmark记录 | 124 | 9,895 | 98.8% | R47 |
| `evidence/sources/R48.md` | R48 | R48 · llama.cpp 与 vLLM 推理性能评测工具2026年版本 | 6,456 | 2,728 | 29.7% | R48 |
| `evidence/sources/R49.md` | R49 | R49 · 大模型性能评估框架集合 | 2,939 | 287 | 8.9% | R49 |
| `evidence/sources/R50.md` | R50 | R50 · 使用llama.cpp进行模型转换和量化，再使用ollama自定义模型。 | 1,655 | 834 | 33.5% | R50 |
| `evidence/sources/README.md` | R00 | R01–R50 原文索引 | 2,557 | 0 | 0.0% | R01, R02, R03, R04, R05, R06, R07, R08, R09, R10, R11, R12, R13, R14, R15, R16, R17, R18, R19, R20, R21, R22, R23, R24, R25, R26, R27, R28, R29, R30, R31, R32, R33, R34, R35, R36, R37, R38, R39, R40, R41, R42, R43, R44, R45, R46, R47, R48, R49, R50 |
| `meta/evidence-policy.md` | EV03 | 证据使用与数据边界 | 890 | 0 | 0.0% | E21, E23, E24, E25, E26, E32 |
| `meta/known-conflicts.md` | EV06 | 已知口径冲突 | 479 | 0 | 0.0% | - |
| `meta/metrics.md` | EV04 | 性能指标口径 | 557 | 0 | 0.0% | - |
| `meta/style-guide.md` | EV05 | 三卷写作与章节模板 | 499 | 0 | 0.0% | - |
