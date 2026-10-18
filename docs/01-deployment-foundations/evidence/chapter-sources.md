# FlowUs 文章与章节对应表

[全书目录](../SUMMARY.md) · [历史数据与条件](README.md) · [本轮CPU完整记录](../practice/first-service/README.md)

## 1. 怎样使用这些材料？

原《大模型部署适配交付知识体系框架》决定本书六部分、五层及各层节标题。内容从作者FlowUs空间中与部署、编译、格式、量化、缓存、服务、压测和多硬件相关的技术文章整理，按当前知识点连接。未将空间所有文章逐字复制到仓库，也不声称公开了整个私人知识库。

历史命令改为统一公开路径与回环地址，必要时补上执行顺序和检查方法。没有结果的建议命令仍标为操作说明；失败与成功分别保留。新写教学程序不假称是历史原件。

## 2. 五层正文分别参考哪些文章？

| 总章 | FlowUs技术文章或记录主题 | 本书专题与采用内容 |
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

## 3. 本轮新增的完整执行

Windows CPU演练实际下载固定官方二进制和Qwen3-0.6B-Q8_0，核验模型后运行服务、三道功能题、畸形JSON、八个流式请求、metrics和三轮引擎基准。完整输入、代码与12个结果文件已经公开。

它与FlowUs历史工程分别记录。本轮没有重跑GPU/NPU历史成绩，也没有把新代码的预期输出当作已执行结果。总验收明确失败，详情见[演练教程](../practice/first-service/README.md)。

## 4. 概念与旧记录怎样修订？

保留有用的版本、步骤、错误和数据，同时修订格式/量化混称、K-quant解释、CUDA版本关系、4080 NVLink、Docker显存限制与前缀缓存实现等问题。修订列表见[附录B](../appendices/references.md)。

公开材料不含私人页面链接、空间导出、账户、凭据、实际节点地址与未经授权的业务输入。原框架图使用用户提供的附件；其他私人笔记图片未直接搬运为本书实测截图。
