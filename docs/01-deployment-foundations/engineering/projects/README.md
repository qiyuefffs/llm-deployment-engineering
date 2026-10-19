---
id: T49
title: "端侧模型项目文档索引"
type: tutorial
volume: book
layer: 0
platform: "general"
device: "general"
status: historical
source_ids: []
updated: 2026-10-19
summary: "8 个项目独立成文，保留环境与制品、实际命令、测试矩阵、原始计时复算、结果、失败与未验证项。"
---

# 端侧模型项目文档索引

[通用性能优化测试方法论](../edge-llm-performance-methodology.md) · [工程实例索引](../../cases/README.md)

本目录保持 8 个项目各自独立成文，具体写到环境与制品、运行参数、操作检查点、
负载构造、计时和资源采样、结果复算、失败与未验证项。命令保留技术内容，
私人路径、节点、身份和模型摘要使用占位符；脱敏后的补充原文见
[E21–E32](../../evidence/records/projects.md)。

## 项目列表

| 文档 | 推荐路线 | 代表性结果 |
| --- | --- | --- |
| [MiniMax-M2.7 多机推理](01-minimax-m27.md) | HIP/ROCm + llama.cpp RPC | 双机部署、2/5 槽位、加载与请求 timing；三机摘要单列待回链 |
| [DeepSeek V4 Flash](02-deepseek-v4-flash.md) | DwarfStar、Lucebox、vLLM 按目标选择 | 单机短生成约 16 tok/s；Lucebox 约 23 tok/s；三机长 Prompt Prefill 约为单机 2.54 倍 |
| [Qwen3.6-35B-A3B](03-qwen36-35b-a3b.md) | 并发首选 HIP 双副本，单路可测试 Vulkan MTP | 72 个固定总上下文场景；双机双副本适合并发扩容 |
| [Qwen3.8-27B 与 Flash-Next](04-qwen38-27b-flash-next.md) | 27B 用 Vulkan；Flash-Next 用 cooperative matrix | 27B 约 20.9 tok/s；Flash-Next 4K 前缀 Prefill 提升约 32% |
| [GLM-5.3-Flash](05-glm-53-flash.md) | 随制品记录：BALANCED / HYBRID | 架构、量化类型、MTP sweep 和作者质量回退；未发现本机独立实测 |
| [vLLM ROCm 文本与多模态](06-vllm-rocm.md) | Docker/原生 vLLM + OpenAI API | Qwen3-VL 并发 32 输出约 469 tok/s；W4A16 TP2 改善加载与 Prefill |
| [MiniMax-H3 视频/音频生成](07-minimax-h3.md) | stable-diffusion.cpp HIP + FA + offload | 正式任务约 39:51，比 ComfyUI 快约 3:43 |
| [Qwen-Image 2.1](08-qwen-image-21.md) | sd.cpp HIP 或 MIOpen immediate 保护路径 | VAE 解码 178.28 秒降至 1.87 秒；Turbo 1024/8 步约 45.9 秒 |

## 阅读方式

1. 先看任务、记录日期、来源性质和环境，区分实际报告与部署方案。
2. 按具体命令与检查点验收设备、制品、模型加载及真实输出。
3. 按对应章节的矩阵、冷暖、计时与资源方法复测，不跨口径排名。
4. 对照结果、失败和未验证项，再沿证据链接核对原始条件。

## 共同约束

- 先固定模型 revision、分片、量化、引擎、后端和上下文。
- 先通过 health、models、真实生成和完整性检查，再测性能。
- Prefill、Decode、TTFT、E2E 和输出吞吐分开记录。
- 失败请求和不支持的组合不能按 0 或空白混入均值。
- MTP、P/D、RPC 和低精度 kernel 都必须用完整请求验收。
- 公开文档保留必要的脱敏技术日志，过滤内部地址、私人路径、身份和凭据。

