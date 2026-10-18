# 全书目录

《大模型部署适配工程基础》按原知识框架的六部分、五层能力组织。总章建立完整理解，下面的专题保存连续操作，实例保留输入、产物与验收。建议先读前言与第一部分，再依次进入五层。

## 开始阅读

- [封面与概览](README.md)
- [写在前面：本书怎样阅读](00-preface.md)
- [完整操作实例：第一个本地推理服务](practice/first-service/README.md)

## 第一部分：整体知识体系地图

- [一条主线与五层能力模型](01-knowledge-map.md)

## 第二部分：五层能力详细框架

- [第二部分总章](02-capability-layers/README.md)
- [第1层：硬件后端适配层](02-capability-layers/01-hardware-backends.md)
  - [NVIDIA：驱动、CUDA、构建与架构](chapters/hardware/nvidia.md)
  - [AMD：ROCm、HIP、Vulkan与共享内存](chapters/hardware/amd.md)
  - [Intel：GPU、NPU、SYCL与IR](chapters/hardware/intel.md)
  - [Apple：Metal、MLX与功能边界](chapters/hardware/apple.md)
  - [昇腾：芯片、CANN、插件与测试](chapters/hardware/ascend.md)
- [第2层：模型格式与量化层](02-capability-layers/02-model-formats-quantization.md)
  - [从原始权重到可加载的GGUF](chapters/models/gguf-conversion.md)
  - [量化选择：从放得下到用得好](chapters/models/quantization.md)
- [第3层：推理框架层](02-capability-layers/03-inference-frameworks.md)
  - [vLLM：从目录到可测量的服务](chapters/frameworks/vllm-service.md)
  - [llama.cpp：构建、加载、接口与停止](chapters/frameworks/llama-cpp.md)
  - [OpenVINO：固定IR的GPU推理](chapters/frameworks/openvino.md)
- [第4层：显存与性能优化层](02-capability-layers/04-memory-performance.md)
  - [性能测试：边界、负载、指标与结果](chapters/performance/benchmarking.md)
  - [KV、缓存与调度](chapters/performance/cache-scheduling.md)
  - [多卡与多节点：容量、通信与收益](chapters/performance/parallelism.md)
  - [推测解码：MTP与DFlash结果分析](chapters/performance/speculative-decoding.md)
- [第5层：工程交付层](02-capability-layers/05-engineering-delivery.md)
  - [环境封装、启停与回滚](chapters/delivery/environment-operations.md)
  - [API、监控与验收](chapters/delivery/api-monitoring.md)

## 第三部分：核心概念解释库

- [十个概念：一句话、工程解释与分析](03-core-concepts.md)

## 第四部分：项目复盘模板

- [标准项目十项记录与多硬件模板](04-project-review.md)
- [可填写的适配记录](templates/adaptation-record.md)
- [可填写的实验记录](templates/experiment-record.md)

## 第五部分：个人知识库目录设计

- [原有八个目录与正文索引](05-knowledge-base.md)

## 第六部分：故障排查速查表

- [从失败阶段找到检查入口](06-troubleshooting.md)

## 附录与实践来源

- [附录A：常用命令](appendices/commands.md)
- [附录B：参考资料与原稿修订](appendices/references.md)
- [FlowUs文章与章节对应表](evidence/chapter-sources.md)
- [历史工程条件与结果说明](evidence/README.md)

## 配套材料

### 工程实例检索

以下实例归入原来的五层，按问题跳转即可。参数与结果均在对应正文展开。

| 想解决的问题 | 详细操作与分析 |
| --- | --- |
| 12GB显存运行30B模型，怎样判断混合推理是否可用 | [RTX2060：卸载、内存、一次完整生成计时](chapters/hardware/nvidia.md#七完整工程实例rtx-2060-12gb-怎样运行大于显存的模型) |
| 395物理内存够大，HIP却只能用约63GB | [AMD：GTT/TTM修复与五机HIP RPC全流程](chapters/hardware/amd.md#六完整操作把395五机hip-rpc记录展开) |
| W7900两台机器怎样组成一个服务 | [Ray、通信、TP8×PP2与分阶段排错](chapters/performance/parallelism.md#八完整操作w7900双节点怎样形成一个服务) |
| Mac编译成功却无法执行某个GGUF | [Metal工具链、张量命名与type42故障](chapters/hardware/apple.md#七完整操作metal构建应该怎样验收) |
| Mac只输出思考，图片又报500 | [vllm-metal模板、采样与视觉encoder边界](chapters/hardware/apple.md#八完整操作vllm-metal文本服务与模板排错) |
| Intel GPU如何选择Vulkan、SYCL和IR | [23层GPU/10层CPU与分阶段对照](chapters/hardware/intel.md#六完整对照vulkan与sycl怎样测得清楚) |
| NPU速度快但音频不对，该如何验收 | [ASR三轮、TTS全NPU失败与48例Kokoro复测](chapters/frameworks/openvino.md#七完整工程记录whisper-asr的冷启动与热推理) |
| 图片怎样发送到云端/本地服务并保存证据 | [公开输入生成、base64、完整SSE客户端](chapters/frameworks/vllm-service.md#七从图片文件到流式答案的完整链路) |
| 模型下载、转换、量化与导入怎样连起来 | [HF→GGUF→量化、aria2与Ollama](chapters/models/gguf-conversion.md) |
| AWQ4/8bit在不同结构上表现怎样 | [四组部署、实际token与完整延迟表](chapters/models/quantization.md#八完整工程gb10的gemma4-awq四组比较) |
| 重复长文怎样验证前缀缓存收益 | [MLX-VLM APC配置、冷暖/租户/挤出实验](chapters/performance/cache-scheduling.md#八mlx-vlm-apc从配置到冷暖缓存实验) |
| MTP和DFlash的收益怎样分析 | [服务参数、接受统计、吞吐与流式对照](chapters/performance/speculative-decoding.md#六gemma-mtp先把服务条件恢复出来) |
| oMLX并发提高后怎样选工作点 | [三档完整成绩、有限并发与资源采样](chapters/performance/benchmarking.md#十omlx完整并发结果与工作点选择) |
| 升级失败怎样回到已验证版本 | [运行卡、资源回收与TTS回滚实例](chapters/delivery/environment-operations.md#七一个可维护的部署目录应该怎样摆放) |

[离线书籍页面](book.html)可下载后直接用浏览器打开，支持目录、全文搜索和上下章。完整代码与JSON、日志等仍保留为普通文件，可随整个仓库下载。

生成阅读版：`python tools/build_deployment_book.py`。构建依赖和入口见[构建说明](../../tools/README.md)。本目录是基础知识体系，独立实战继续保存在仓库的Case目录中。
