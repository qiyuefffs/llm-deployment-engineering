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

[离线书籍页面](book.html)可下载后直接用浏览器打开，支持目录、全文搜索和上下章。完整代码与JSON、日志等仍保留为普通文件，可随整个仓库下载。

生成阅读版：`python tools/build_deployment_book.py`。构建依赖和入口见[构建说明](../../tools/README.md)。本目录是基础知识体系，独立实战继续保存在仓库的Case目录中。
