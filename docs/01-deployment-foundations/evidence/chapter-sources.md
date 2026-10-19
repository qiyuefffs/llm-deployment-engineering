---
id: EV01
title: "FlowUs 文章与章节对应表"
type: evidence
volume: evidence
layer: 0
platform: "general"
device: "general"
status: historical
source_ids: [R01, R02, R03, R04, R05, R06, R07, R08, R09, R10, R11, R12, R13, R14, R15, R16, R17, R18, R19, R20, R21, R22, R23, R24, R25, R26, R27, R28, R29, R30, R31, R32, R33, R34, R35, R36, R37, R38, R39, R40, R41, R42, R43, R44, R45, R46, R47, R48, R49, R50]
updated: 2026-10-19
summary: "原《大模型部署适配交付知识体系框架》决定六部分、五层及各层节编号。主框架按组件、参数和工程检查组织；50份相关FlowUs技术文章的完整正文写入设备工程实例，保留命令、表格、错误与后续实验。隐私与认证脱敏，篇目与保留范围见源文覆盖清单。"
---

# FlowUs 文章与章节对应表

[知识体系目录](../SUMMARY.md) · [历史数据与条件](records/README.md) · [本轮CPU完整记录](../cases/C14-windows-cpu/README.md)

## 1. 怎样使用这些材料？

原《大模型部署适配交付知识体系框架》决定六部分、五层及各层节编号。主框架按组件、参数和工程检查组织；50份相关FlowUs技术文章的完整正文写入[设备工程实例](../cases/README.md)，保留命令、表格、错误与后续实验。隐私与认证脱敏，篇目与保留范围见[源文覆盖清单](source-coverage.json)。

平台专题中的执行示例采用统一公开路径；完整源文保留技术参数并替换私人路径和节点，历史监听配置按原文标识。实例入口补执行顺序和技术修订。没有结果的建议命令仍标为操作说明；失败与成功分别保留。新写程序不假称是历史原件。

## 2. 五层正文分别参考哪些文章？

| 总章 | FlowUs技术文章或记录主题 | 本体系专题与采用内容 |
| --- | --- | --- |
| 第1层1.1—1.4 | 4090 CUDA、DGX Spark编译、CUDA链接排错 | [NVIDIA](../chapters/hardware/nvidia.md)：驱动/Toolkit/wheel、SM与kernel |
| 第1层1.2—1.4 | 780M教程、395五机HIP RPC、ROCm环境 | [AMD](../chapters/hardware/amd.md)：gfx、版本隔离、GTT/TTM |
| 第1层1.2—1.4 | Qwen3.5-9B Intel对比、Windows视觉部署 | [Intel](../chapters/hardware/intel.md)：后端、设备与任务分开 |
| 第1层1.2—1.4 | Mac Metal构建、vllm-metal、oMLX操作 | [Apple](../chapters/hardware/apple.md)：制品与文本/视觉支持 |
| 第1层1.2—1.4 | 昇腾310P部署、插件安装与压测 | [昇腾](../chapters/hardware/ascend.md)：芯片/镜像配套与实际请求数 |
| 第2层2.1—2.6 | GB10 llama.cpp、Qwen转GGUF、量化与Ollama导入 | [GGUF转换](../chapters/models/gguf-conversion.md)：完整目录→F16→Q4→加载 |
| 第2层2.3—2.6 | GGUF量化、Intel IR INT4/INT8、Gemma AWQ对比 | [量化](../chapters/models/quantization.md)：容量、kernel、质量与性能 |
| 第3层3.1—3.3 | DGX Spark vLLM源码部署Qwen FP8、早期vLLM安装 | [vLLM服务](../chapters/frameworks/vllm-service.md)：构建、启动、API与突发负载 |
| 第3层3.4—3.5 | CUDA/HIP/Vulkan/SYCL/Metal构建与加载 | [llama.cpp](../chapters/frameworks/llama-cpp.md)：独立构建、服务与基准 |
| 第3层3.1/3.6 | Intel OpenVINO对比与IR部署 | [OpenVINO](../chapters/frameworks/openvino.md)：依赖、固定制品、Pipeline与失败 |
| 第4层4.1—4.6 | 压测工具总文、vLLM bench、EvalScope、oMLX报告 | [性能测试](../chapters/performance/benchmarking.md)：负载、边界、并发和指标 |
| 第4层4.2—4.6 | KV、Prefill、Prefix Cache学习与验证笔记 | [缓存与调度](../chapters/performance/cache-scheduling.md)：概念修订与实验顺序 |
| 第4层4.6 | 双4080、多节点排障、AMD五机RPC | [多设备](../chapters/performance/parallelism.md)：通信关口、容量与收益 |
| 第4层4.6 | Gemma关闭/开启MTP、GB10集成DFlash | [推测解码](../chapters/performance/speculative-decoding.md)：配对结果与多变量归因 |
| 第5层5.1—5.3 | Docker Runtime、双卡容器、昇腾镜像、Intel服务启停 | [环境与运维](../chapters/delivery/environment-operations.md)：封装、启停与恢复 |
| 第5层5.2—5.3 | OpenAI兼容接口、压测与服务监控 | [API与监控](../chapters/delivery/api-monitoring.md)：契约、指标和验收 |

第三部分解释原来的十个概念；第四部分将工程材料组织为十项项目记录；第五部分保留八个原目录作为索引；第六部分从上述真实失败中提取排查入口。

### 本次扩写具体采用哪些工程过程

| 文章主题 | 正文展开的位置 | 直接采用的材料 |
| --- | --- | --- |
| RTX2060 Qwen3 Q6/Q5混合推理 | NVIDIA第七节 | i5/32GB/12GB、原参数、9/182token与计时、资源观察、并发证据范围 |
| 395五机HIP RPC Kimi-K2.5-Q2 | AMD第六节 | BIOS2GB、GTT/TTM数字、DKMS模块、修复、build、RPC、split、加载监控 |
| W7900八卡及双节点70B/671B | AMD第七节、多设备第八—九节 | ROCm容器、OpenAI入口修正、Ray角色、TP8×PP2、资源与通信检查 |
| Mac Metal源码构建 | Apple第七节 | Xcode/clang/CMake/Ninja、库与shader、9d36408、hc_head_base/type42 |
| vllm-metal编译与文本/视觉 | Apple第八节 | 完整依赖表、_rs导入位置、模板/采样、encoder未实现与EngineDead |
| MLX-VLM多视觉模型与API | Apple第九节、vLLM图像链路 | Metal检查、CLI/server、图像字段、processor分辨率与切片参数 |
| oMLX操作与性能 | Apple第十节、压测第十节 | 父目录发现、load流程、内存快照、三档完整延迟与吞吐 |
| MLX-VLM APC | 缓存第八—九节 | 原环境变量、块/磁盘预算、tenant、stats/reset、KV量化互斥 |
| Intel GPU对比 | Intel第六节、OpenVINO主教程 | pp/tg、23/10层、Mesa25.2.8与26.1.4、HTTP/Pipeline边界 |
| Intel语音专项 | OpenVINO第七—十二节 | Whisper三轮、BabelVox设备分工/三轮、CP shape与质量失败、Qwen TTS、Kokoro48例 |
| GB10 VL/Omni/docling | NVIDIA第八节、vLLM第七—八节 | 镜像、原端口和预算、base64/SSE流程、功能分项 |
| Gemma4 AWQ4/8 | 量化第八节 | 26B-A4B/31B四组、200请求、实际token、TTFT/TPOT/ITL/E2E完整表 |
| Gemma4 MTP关闭/开启 | 推测解码第六—七节 | 主/assistant、服务预算、三档配对、接受计数与流式分析 |
| GB10 DFlash编译与测试 | 推测解码第八—九节 | 2cc008e7b、CUDA/torch、drafter、两套配置与完整延迟 |
| Intel IPEX-LLM与Ollama | Intel第七节、GGUF导入节 | Python3.11历史路线、程序来源、SYCL变量和模板修订 |

上述参数与数值保留工程意义，私人路径与节点改为公开约定。公开视觉图、客户端与aria2清单生成器属于本次补齐的教学材料，未冒充历史原件。

## 3. 本轮新增的完整执行

Windows CPU演练实际下载固定官方二进制和Qwen3-0.6B-Q8_0，核验模型后运行服务、三道功能题、畸形JSON、八个流式请求、metrics和三轮引擎基准。完整输入、代码与12个结果文件已经公开。

它与FlowUs历史工程分别记录。本轮没有重跑GPU/NPU历史成绩，也没有把新代码的预期输出当作已执行结果。总验收明确失败，详情见[演练教程](../cases/C14-windows-cpu/README.md)。

## 4. 概念与旧记录怎样修订？

保留有用的版本、步骤、错误和数据，同时修订格式/量化混称、K-quant解释、CUDA版本关系、4080 NVLink、Docker显存限制与前缀缓存实现等问题。修订列表见[附录B](../appendices/references.md)。

公开材料不含私人页面链接、空间导出、账户、凭据、实际节点地址与未经授权的业务输入。原框架图使用用户提供的附件；其他私人笔记图片未直接搬运为本体系实测截图。

## 5. 完整技术原文到设备实例的对应

| 实例文件 | 完整技术文章 |
| --- | --- |
| [nvidia-rtx2060](../cases/C01-rtx2060/README.md) | R01 nvidai-llamacpp-qwen3:30-a3b-q6测试记录；R02 nvidai-llamacpp-qwen3:30-a3b-q6基准性能测试记录；R03 nvidai-llamacpp-qwen3:32B-q5基准性能测试记录 |
| [nvidia-dual-gpu](../cases/C02-dual-4080/README.md) | R04 服务器：Nvidia显卡：Ubuntu22.04+VLLM+Docker双卡部署Deepseek-r1:32B(Int4) |
| [nvidia-gb10](../cases/C03-gb10/README.md) | R05 NVIDIA GB10 ARM编译llamacpp；R06 nvidia GB10设备（arm64架构）编译vllm；R07 DGX Spark适配编译vllm部署Qwen3.6-35B-A3B模型（bf16/fp8精度）；R08 NVIDIA GB10部署Qwen3-30B-A3B-Instruct-2507；R09 DGX GB10部署Gemma-4系列AWQ量化模型；R10 DGX Spark GB10部署gemma-4系列模型及关闭MTP推理加速；R11 DGX Spark GB10部署gemma-4系列模型及MTP推理加速；R12 DGX Spark GB10编译DFlash推理加速模块集成到vllm中 |
| [nvidia-gb10-multimodal](../cases/C04-gb10-multimodal/README.md) | R13 GB10部署Qwen3-VL-8B模型；R14 nvidia GB10 部署Qwen2.5-VL-7B；R15 GB10部署Qwen3-VL-30B-A3B；R16 NVIDIA GB10版本vllm部署Qwen3‑Omni‑30B‑A3B‑Instruct；R17 NVIDIA GB10 vllm部署granite-docling-258M |
| [amd-780m](../cases/C05-radeon-780m/README.md) | R18 AMD 780M-GPU 适配教程；R19 AMD适配模型（GPU-780M，ＣＰＵ　－8845HS）；R20 AMD：使用Ollama框架将Llama3.1 8b部署在AMD的GPU |
| [amd-8060s](../cases/C06-radeon-8060s/README.md) | R21 Qwen3.6-35B-A3B 部署与推理文档；R22 Qwen3.6-35B-A3B BF16 推理优化记录 |
| [amd-395-rpc](../cases/C07-amd-395-rpc/README.md) | R23 AMD Strix Halo 395 五机 HIP RPC 串联部署 Kimi-K2.5-Q2 实战文档；R24 AMD 395 llamcpp+rpc编译流程；R25 AMD 395 llamacpp rpc服务功能环境测试脚本 |
| [amd-w7900](../cases/C08-w7900/README.md) | R26 单节点八卡服务器（W7900*8,48*8）DeepSeek-R1-AWQ-INT4部署；R27 W7900双卡部署Qwen3:30b-A3b；R28 服务器：AMD显卡：Ubuntu22.04+VLLM+Docker双卡部署Deepseek-r1:32b/70b；R29 AMD单节点四卡DS-70B-fp16测试命令；R30 双节点模型部署70B验证；R31 双节点模型部署70B-2.0资源调度验证；R32 双节点，再次推理DS-70B；R33 Deepseek-R1-671b双节点部署；R34 多节点部署排障 |
| [intel-arc-npu](../cases/C09-intel-arc-npu/README.md) | R35 Qwen3.5-9B Intel openvino 平台推理对比报告；R36 Qwen3.5-9B INT4 IR 多模态视觉推理测试报告；R37 使用ipex-llm进行量化并制作ollama模型，部署在Intel集显。；R38 Intel NPU进行模型推理：deepseek-r1:1.5b,7b,8b |
| [apple-metal](../cases/C10-m3-metal/README.md) | R39 llama.cpp 在 Mac Studio (Apple Silicon) 上的编译指南 |
| [apple-mlx](../cases/C11-m3-mlx/README.md) | R40 vllm-metal 编译与推理记录；R41 mlx-vlm 多视觉模型推理与 API 调用指南；R42 oMLX Mac 推理操作流程；R43 oMLX 推理框架性能测试报告与压测流程；R44 Mac 设备推理框架分类总结 |
| [ascend-310p](../cases/C12-ascend-310p/README.md) | R45 华为昇腾310P3推理Qwen3-32B；R46 华为昇腾310p3：qwen3-32b与qwen3-235b-a22b-2507测试；R47 昇腾310P3部署Qwen3-32B benchmark记录 |
| [benchmark-tools](../appendices/benchmark-tools.md) | R48 llama.cpp 与 vLLM 推理性能评测工具2026年版本 ；R49 大模型性能评估框架集合 |
| [gguf-ollama](../appendices/gguf-ollama.md) | R50 使用llama.cpp进行模型转换和量化，再使用ollama自定义模型。 |
