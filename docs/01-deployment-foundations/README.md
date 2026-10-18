# 大模型部署适配知识体系

![大模型部署适配五层能力框架](assets/edge-llm-deployment-framework-original.png)

图注：作者原始框架。目录沿用六部分、五层能力及1.1～5.3节编号；图中的格式、精度、量化与后端分类以正文技术说明为准。

> 适用方向：大模型部署、端侧适配、推理优化、多硬件工程交付。
> 核心产物：可追溯环境、可加载模型、可调用服务、可对照基线、优化实验、验收与回滚记录。

## 0. 总体定位

```text
模型选择 → 格式转换/量化 → 硬件后端适配 → 引擎构建与部署
 → 权重/KV/工作区预算 → 功能基线 → 性能压测 → 瓶颈定位
 → 单项或组合优化 → API/监控 → 交付与回滚
```

知识点按“机制、参数、执行阶段、诊断证据”组织；平台工程保存完整操作链路。历史FlowUs技术文章直接写入对应实例，保留命令、日志、性能表、失败和后续实验，不用摘要替代过程。

**[五层框架与完整目录](SUMMARY.md) · [各GPU部署优化实例](engineering/README.md) · [环境与数据约定](00-preface.md) · [可离线搜索的页面](book.html)**

## 第一部分：整体知识体系地图

[七个工程模块与五层能力](01-knowledge-map.md)：任务约束、阶段输入输出、交付关口与项目目录。

## 第二部分：五层能力详细框架

| 能力层 | 核心技术 | 主要参数 / 产物 |
| --- | --- | --- |
| [1.硬件后端适配](02-capability-layers/01-hardware-backends.md) | CUDA/HIP/SYCL/Vulkan/Metal/CANN/MUSA、驱动与编译、通信 | arch/gfx/ABI、CMakeCache、镜像digest、最小设备执行 |
| [2.模型格式与量化](02-capability-layers/02-model-formats-quantization.md) | HF/GGUF/IR、W/A/KV精度、AWQ/GPTQ、分组/尺度/kernel | revision、SHA256、quantization_config、模板、质量基线 |
| [3.推理框架](02-capability-layers/03-inference-frameworks.md) | vLLM、llama.cpp、OpenVINO、MLX、加载与调度 | max-model-len、seqs、batched-tokens、ngl、b/ub、API |
| [4.显存与性能](02-capability-layers/04-memory-performance.md) | KV、prefill/decode、缓存、并发、TP/PP/EP、MTP/DFlash | TTFT/TPOT/ITL、吞吐、p95/p99、内存峰值、质量 |
| [5.工程交付](02-capability-layers/05-engineering-delivery.md) | 容器/环境、SSE、监控、限流、验收、回滚 | run-id、有效命令、逐请求数据、部署/恢复入口 |

## 各硬件完整工程实例

| 硬件 | 完整部署适配与加速优化 |
| --- | --- |
| NVIDIA | [RTX2060混合卸载](engineering/nvidia-rtx2060.md) · [RTX4080/A6000双卡](engineering/nvidia-dual-gpu.md) · [GB10构建、FP8、AWQ、MTP与DFlash](engineering/nvidia-gb10.md) · [GB10多模态](engineering/nvidia-gb10-multimodal.md) |
| AMD | [780M Windows HIP](engineering/amd-780m.md) · [8060S Vulkan Q4/BF16](engineering/amd-8060s.md) · [395五机HIP RPC](engineering/amd-395-rpc.md) · [W7900单机/多节点](engineering/amd-w7900.md) |
| Intel | [Arc GPU三后端、NPU、ASR/TTS完整记录](engineering/intel-arc-npu.md) |
| Apple | [M3 Ultra Metal/GGUF](engineering/apple-metal.md) · [MLX、APC、oMLX并发](engineering/apple-mlx.md) |
| 昇腾 | [310P3 CANN、Qwen3、插件与压测](engineering/ascend-310p.md) |
| MUSA | [设备适配、构建、API与优化验证流程](engineering/musa.md)，待设备实测 |
| CPU | [固定Windows完整运行与实际结果](practice/first-service/README.md) |

## 第三至六部分

- [第三部分：核心概念解释库](03-core-concepts.md)：十个核心机制及参数影响。
- [第四部分：项目复盘模板](04-project-review.md)：硬件、制品、部署、排错、实验、验收十项记录。
- [第五部分：个人知识库目录设计](05-knowledge-base.md)：八个主题目录与工程资料组织。
- [第六部分：故障排查速查表](06-troubleshooting.md)：按失败阶段定位、验证和回归。

## 完整材料与证据

[50份源文保留清单](evidence/source-coverage.json) · [章节与文章映射](evidence/chapter-sources.md) · [历史测量JSON](evidence/measurements.json) · [离线核算程序](examples/verify_records.py) · [参考资料](appendices/references.md)

技术记录保留可公开设备、版本、配置、性能和错误。私人路径、节点、认证及附件地址脱敏。历史GPU/NPU成绩标明测试条件，本轮未重新运行；资料缺项与失败不会改写成成功。
