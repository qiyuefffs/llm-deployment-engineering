---
id: T39
title: "硬件部署适配与加速优化实例索引"
type: tutorial
volume: book
layer: 0
platform: "general"
device: "general"
status: historical
source_ids: []
updated: 2026-10-19
summary: "每个硬件入口包含环境、部署适配顺序、基线、优化参数、原始结果、失败与验收，以及对应FlowUs完整技术文章。表中的“已记录”表示作者历史笔记有该内容；不等于本轮重新测试或材料已达到独立Case的完整复现要求。"
---

# 硬件部署适配与加速优化实例索引

[知识体系首页](../README.md) · [五层能力目录](../SUMMARY.md) · [源文保留清单](../evidence/source-coverage.json)

## 实例矩阵

每个硬件入口包含环境、部署适配顺序、基线、优化参数、原始结果、失败与验收，以及对应FlowUs完整技术文章。表中的“已记录”表示作者历史笔记有该内容；不等于本轮重新测试或材料已达到独立Case的完整复现要求。

| 硬件 | 实例与模型 | 部署适配 | 加速优化与结果 | 状态 |
| --- | --- | --- | --- | --- |
| RTX2060 12GB | [Qwen3 Q6/Q5](../cases/C01-rtx2060/README.md) | CUDA、GGUF、CPU/GPU混合卸载 | 层数/量化/主机内存；一次decode约5.26token/s | 历史单次记录 |
| RTX4080×2 | [DeepSeek32B GPTQ INT4](../cases/C02-dual-4080/README.md) | Docker、Toolkit、TP2、PCIe | ctx/seqs/memory/chunked；35→55→52token/s | 多变量、负载不完整 |
| A6000×2 | [DeepSeek70B FP8目录](../cases/C02-dual-4080/README.md) | 双48GB、TP2、kernel核查 | 17.1→17.5token/s；Ampere无原生FP8矩阵能力 | 历史观察，核查实际kernel |
| GB10 | [Qwen FP8、Gemma AWQ/MTP/DFlash](../cases/C03-gb10/README.md) | ARM64、CUDA13、源码与扩展 | 四组量化、三组MTP、DFlash组合对照 | 有完整汇总，原始明细缺项 |
| GB10多模态 | [VL、Omni、Docling](../cases/C04-gb10-multimodal/README.md) | processor、encoder、图像/音频协议 | 分辨率、token预算、缓存、调度实验 | 各能力分项验收 |
| Radeon780M | [8845HS Windows HIP/Ollama](../cases/C05-radeon-780m/README.md) | gfx1103社区库、DLL隔离、模型加载 | CPU/GPU回退、上下文与UMA预算 | 部署步骤，无完整性能表 |
| Radeon8060S | [395 Vulkan Q4/BF16](../cases/C06-radeon-8060s/README.md) | 全层卸载、GDN、共享内存 | Q4 22.9→47.2→58.4；BF16 10.8→10.1token/s | 有调参表，质量需补 |
| 8060S×5机 | [Kimi HIP RPC](../cases/C07-amd-395-rpc/README.md) | GTT/TTM、DKMS、同版本构建与分发 | split与小工作区；不补造多机加速比 | 有容量与加载过程 |
| W7900 | [双/四/八卡与双节点](../cases/C08-w7900/README.md) | ROCm/RCCL、Ray、TP/PP | 单机→多机、通信、rank内存、资源调度 | 完整操作迭代，性能明细不全 |
| Intel Arc | [Qwen3.5-9B GPU三后端](../cases/C09-intel-arc-npu/README.md) | Vulkan/SYCL/IR、设备与精度对照 | INT4/INT8、Mesa、23GPU/10CPU层 | 原始三轮与管线指标 |
| Intel NPU | [ASR/TTS与Kokoro](../cases/C09-intel-arc-npu/README.md) | shape、NPUW、设备分工 | 实时性/质量/RSS；保留全NPU失败与回滚 | 48例CPU与NPU失败 |
| Apple M3 Ultra | [Metal/GGUF](../cases/C10-m3-metal/README.md) | Xcode、shader、tensor/type兼容 | 实际卸载、ctx/ubatch/FA验证 | 特定制品加载失败如实保留 |
| Apple M3 Ultra | [MLX/APC/oMLX](../cases/C11-m3-mlx/README.md) | 原生扩展、模板、VLM、模型发现 | c1/2/4：29.38/41.11/55.15token/s | 文本/视觉范围分开 |
| 昇腾310P3 | [Qwen3-32B](../cases/C12-ascend-310p/README.md) | CANN、设备节点、插件、FP16/TP2 | 单样例长生成约4.5936token/s | 1请求不当十并发 |
| MUSA | [完整验证流程](../cases/C13-musa/README.md) | Toolkit、GGML后端、GGUF、API | CPU→GPU、层数、FA、batch、槽位 | 未找到实测源文，待设备验证 |
| CPU | [固定Windows完整演练](../cases/C14-windows-cpu/README.md) | 固定模型/二进制、SHA256、API | 8请求、3轮引擎、完整实际输出 | 功能2/3，异常返回500，总验收失败 |

## 通用性能优化测试方法论

[通用性能优化测试方法论](edge-llm-performance-methodology.md)只保留共性操作、指标、实验和验收规则；8 个实际项目分别放在[项目文档索引](projects/README.md)，每个项目一份文档，避免把完整操作和敏感信息堆在同一页。

## 每项实例的执行与证据

```text
环境清单 → 制品身份 → 构建日志 → 单请求与接口
 → 无优化基线 → 单项或组合实验 → 性能＋质量＋资源验收
 → 最终命令、启动停止、回滚、限制
```

完整技术文章保留50份，技术段落、代码块、参数、日志与测试表不作摘要删减。隐私字段、认证和私人附件例外；错误技术结论在实例入口说明或原位修订。保留范围与代码围栏数量可查[源文覆盖清单](../evidence/source-coverage.json)。

## 共用工程材料

- [模型转换、量化与Ollama完整原文](../appendices/gguf-ollama.md)
- [压测工具与执行命令完整原文](../appendices/benchmark-tools.md)
- [环境、启停与回滚](../chapters/delivery/environment-operations.md)
- [API、监控与验收](../chapters/delivery/api-monitoring.md)
