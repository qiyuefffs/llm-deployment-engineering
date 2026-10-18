# 大模型部署知识体系目录

六部分、五层能力与原节编号保持对应。从硬件、运行时与模型基础开始，逐步进入引擎执行、性能优化和服务交付；平台操作和完整实测记录用于补充具体工程问题。

## 总览与阅读入口

- [知识体系首页与框架图](README.md)
- [工程资料约定与执行基线](00-preface.md)
- [硬件部署适配与优化实例矩阵](engineering/README.md)
- [CPU实例：固定模型、完整服务与实际验收](practice/first-service/README.md)

## 第一部分：整体知识体系地图

- [模型、硬件与引擎的关系及工程模块](01-knowledge-map.md)

## 第二部分：五层能力详细框架

- [五层框架索引](02-capability-layers/README.md)
- [第1层：硬件、运行时与计算后端（1.1—1.4）](02-capability-layers/01-hardware-backends.md)
  - [NVIDIA：GPU与CUDA、计算库、部署](chapters/hardware/nvidia.md)
    - [RTX2060：混合卸载与Qwen3量化推理](engineering/nvidia-rtx2060.md)
    - [RTX4080/A6000：双卡部署与调参](engineering/nvidia-dual-gpu.md)
    - [GB10：ARM64、FP8、AWQ、MTP与DFlash](engineering/nvidia-gb10.md)
    - [GB10多模态：VL、Omni与Docling](engineering/nvidia-gb10-multimodal.md)
  - [AMD：GPU与ROCm、HIP、计算库、部署](chapters/hardware/amd.md)
    - [780M：Windows HIP与Ollama完整适配](engineering/amd-780m.md)
    - [8060S：Vulkan卸载与Q4/BF16优化](engineering/amd-8060s.md)
    - [395五机：HIP RPC与GTT修复](engineering/amd-395-rpc.md)
    - [W7900：单机多卡、Ray与TP/PP](engineering/amd-w7900.md)
  - [Intel：硬件、oneAPI、OpenVINO与部署](chapters/hardware/intel.md)
    - [Arc/NPU：三后端与ASR/TTS完整实测](engineering/intel-arc-npu.md)
  - [Mac：统一内存、Metal、MLX与部署](chapters/hardware/apple.md)
    - [M3 Ultra：Metal构建与GGUF排错](engineering/apple-metal.md)
    - [M3 Ultra：MLX、APC与oMLX并发](engineering/apple-mlx.md)
  - [昇腾：芯片、CANN、插件与测试](chapters/hardware/ascend.md)
    - [310P3：完整部署、压测与故障记录](engineering/ascend-310p.md)
  - [MUSA：完整部署与优化待验证流程](engineering/musa.md)
- [第2层：模型格式与量化层（2.1—2.6）](02-capability-layers/02-model-formats-quantization.md)
  - [HF→GGUF→量化：统一执行流程](chapters/models/gguf-conversion.md)
  - [量化选择与AWQ四组结果](chapters/models/quantization.md)
  - [模型转换与Ollama：完整技术原文](engineering/gguf-ollama.md)
- [第3层：推理框架层（3.1—3.6）](02-capability-layers/03-inference-frameworks.md)
  - [vLLM：完整服务与多模态输入](chapters/frameworks/vllm-service.md)
  - [llama.cpp：构建、加载、接口与停止](chapters/frameworks/llama-cpp.md)
  - [OpenVINO：IR、GPU/NPU与语音工程](chapters/frameworks/openvino.md)
- [第4层：显存与性能优化层（4.1—4.6）](02-capability-layers/04-memory-performance.md)
  - [性能测试：负载、指标与工作点](chapters/performance/benchmarking.md)
  - [KV、缓存与调度](chapters/performance/cache-scheduling.md)
  - [多卡与多节点：容量、通信与收益](chapters/performance/parallelism.md)
  - [推测解码：MTP与DFlash结果分析](chapters/performance/speculative-decoding.md)
  - [压测工具与命令：完整技术原文](engineering/benchmark-tools.md)
- [第5层：工程交付层（5.1—5.3）](02-capability-layers/05-engineering-delivery.md)
  - [环境封装、启停与回滚](chapters/delivery/environment-operations.md)
  - [API、监控与验收](chapters/delivery/api-monitoring.md)

## 第三部分：核心概念解释库

- [十个核心机制：定义、工程解释与参数](03-core-concepts.md)

## 第四部分：项目复盘模板

- [标准项目十项记录与多硬件模板](04-project-review.md)
- [适配记录模板](templates/adaptation-record.md)
- [实验记录模板](templates/experiment-record.md)

## 第五部分：个人知识库目录设计

- [八个主题目录与工程资料组织](05-knowledge-base.md)

## 第六部分：故障排查速查表

- [按失败阶段定位与回归](06-troubleshooting.md)

## 附录与工程证据

- [附录A：常用命令](appendices/commands.md)
- [附录B：参考资料与技术修订](appendices/references.md)
- [文章、实例与五层框架映射](evidence/chapter-sources.md)
- [历史工程条件与测量说明](evidence/README.md)

50份源文的保留范围及代码围栏数量见[源文清单](evidence/source-coverage.json)。设备、模型、参数和历史性能按原条件保留；隐私与认证脱敏，MUSA标注待实测。

[离线检索页面](book.html)支持框架目录、全文搜索、页内目录与上下项。构建：`python tools/build_deployment_book.py`，依赖见[构建说明](../../tools/README.md)。
