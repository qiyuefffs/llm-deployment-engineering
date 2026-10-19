---
id: T10
title: "第五部分：个人知识库目录设计"
type: tutorial
volume: book
layer: 0
platform: "general"
device: "general"
status: historical
source_ids: []
updated: 2026-10-19
summary: "本部分保持原稿的八个主题目录。它们是按工作问题查阅本体系的索引，与前面的五层正文对应，不再复制八套重复教程。项目记录保存发生过的完整过程，知识条目从中提取可复用解释，实验和故障链接同一份原始证据。"
---

# 第五部分：个人知识库目录设计

[总目录](SUMMARY.md) · [上一部分：项目复盘](04-project-review.md) · [下一部分：故障排查](06-troubleshooting.md)

## 本部分概览

本部分保持原稿的八个主题目录。它们是按工作问题查阅本体系的索引，与前面的五层正文对应，不再复制八套重复教程。项目记录保存发生过的完整过程，知识条目从中提取可复用解释，实验和故障链接同一份原始证据。

## 5.1 原有目录与阅读入口

```text
LLM-Inference-Knowledge-Base/
├── 00-项目总览.md
├── 01-硬件后端适配/
├── 02-推理框架/
├── 03-显存与量化/
├── 04-性能优化/
├── 05-多卡多节点/
├── 06-压测与评估/
├── 07-工程服务化/
└── 08-故障排查/
```

总览说明当前有哪些项目、采用哪套环境、完成到哪个关口、产物在哪里。八个主题保存知识入口；具体模型项目仍保持从准备到验收的执行顺序，避免被拆成无法复跑的片段。

### 01-硬件后端适配

先看[硬件总章](02-capability-layers/01-hardware-backends.md)，再进入[NVIDIA](chapters/hardware/nvidia.md)、[AMD](chapters/hardware/amd.md)、[Intel](chapters/hardware/intel.md)、[Apple](chapters/hardware/apple.md)与[昇腾](chapters/hardware/ascend.md)。平台文章保存设备、驱动、工具链、后端和特有故障；共同的API与指标只引用一处。

MUSA等没有完整公开实践材料的平台，保留支持调研与待验证计划，不用其他平台的日志填补。跨平台比较先统一任务、质量与计时边界，再列不同制品和设备限制。

### 02-推理框架

从[框架总章](02-capability-layers/03-inference-frameworks.md)进入[vLLM服务](chapters/frameworks/vllm-service.md)、[llama.cpp](chapters/frameworks/llama-cpp.md)与[OpenVINO](chapters/frameworks/openvino.md)。每条路线单独保存安装、模型、启动、请求、停止和验收，避免在一个教程中不断切换工具。

TensorRT-LLM与SGLang先记录选型与官方支持入口。没有作者实跑材料时，不能在条目标题中标成“已验证部署”。

### 03-显存与量化

[第2层](02-capability-layers/02-model-formats-quantization.md)解释格式与量化，[第4层](02-capability-layers/04-memory-performance.md)解释内存预算。完整操作见[GGUF转换](chapters/models/gguf-conversion.md)与[量化验证](chapters/models/quantization.md)。

这里分别记录权重、KV、激活和工作区，不把模型文件大小当作总运行内存。对每种量化保存方法、位宽、布局、kernel、校准和质量结果，避免只留下“4bit更快”的一句话。

### 04-性能优化

[缓存与调度](chapters/performance/cache-scheduling.md)说明PagedAttention、持续批处理、分块prefill和前缀缓存；[推测解码](chapters/performance/speculative-decoding.md)说明MTP与DFlash观察。每项实验保存基线、变更、任务、原始数据与结论。

多变量方案写为组合观察。吞吐增加时同时查看TTFT、ITL、尾延迟和质量，不能只记一个提升百分比。

### 05-多卡多节点

[多设备专题](chapters/performance/parallelism.md)集中解释TP、PP、DP、EP、通信与RPC。记录实际互连、设备映射、每rank预算和通信验证，控制面、通信与模型生成逐步验收。

容量扩展与速度收益分开写。单机放不下时可以证明多机让模型可运行，但没有同口径基线就不写加速比。

### 06-压测与评估

[压测教程](chapters/performance/benchmarking.md)统一工具、负载、计时和指标。已公开的[CPU完整演练](cases/C14-windows-cpu/README.md)提供下载、服务、请求、失败、基准与原始结果。

性能与质量分开，最后按项目标准一起判断。保留工具原始明细，汇总由程序计算；不修改结果去适应预期结论。

### 07-工程服务化

[环境封装与运维](chapters/delivery/environment-operations.md)处理版本、容器、启停和回滚；[API与监控](chapters/delivery/api-monitoring.md)处理接口、流式、指标与验收。交付清单见[第5层](02-capability-layers/05-engineering-delivery.md)。

反向代理、网关路由和Kubernetes按项目需求追加部署记录，不作为每个端侧项目的必需步骤。先把单实例的模型、接口与恢复验证清楚，再增加基础设施。

### 08-故障排查

[故障速查](06-troubleshooting.md)按失败阶段找到检查入口。完整故障条目保存触发输入、首次错误、环境、判断依据、修复与回归；不要只收藏最终一条修复命令。

## 5.2 每个知识点按原来的七个问题记录

1. **它是什么？** 先一句话说明，再展开必要原理。
2. **解决什么问题？** 描述触发条件与工程影响。
3. **在项目中怎样用？** 链接具体部署和运行记录。
4. **常用参数是什么？** 写版本、含义、条件与影响。
5. **常见问题是什么？** 按阶段描述可观察现象。
6. **怎样排查？** 给检查顺序、日志和最小复现。
7. **怎样用数据证明？** 写输入、原始结果、质量、指标与限制。

这七项是记录内容的检查框架，不要求每段正文都机械重复七个短标签。原理适合连续讲述，操作按步骤展开，比较用表格，证据集中链接。读者先理解问题，再执行操作，最后看检查结果。

## 5.3 项目、知识、实验和故障怎样连接？

以Prefix Cache为例：知识条目解释相同token前缀的状态复用；项目记录保存服务环境与配置；实验记录保存冷前缀、热前缀和不同前缀的请求明细；故障记录解释一次未命中的具体原因。四者引用同一个run-id，不各自手抄一张不同的结果表。

历史汇总缺原始文件时，标注待补证据；只有设备枚举就标注设备可见；短输入通过就写短输入范围。新版本补齐验证后再更新状态，不用“已完成”掩盖功能缺口。

项目达到可复盘状态后，共性操作汇总到[通用性能优化测试方法论](engineering/edge-llm-performance-methodology.md)，每个项目单独写入[项目文档索引](engineering/projects/README.md)。项目页保持独立，不把多个模型的长流程写在同一个窗口章节里。

## 5.4 长期维护

版本、模板、模型或驱动变化时，先判断影响哪一层，再补对应回归。新的成功结果保留新环境，旧结果仍链接旧版本。公开资料从私人笔记中提取工程必要字段，不直接导出整个空间。

一套可用知识库应帮助你找到：问题在哪层、以前哪次遇到、当时凭什么判断、现在能复用什么。知识体系的[章节来源映射](evidence/chapter-sources.md)和[历史结果](evidence/records/README.md)就是这种连接方式。
