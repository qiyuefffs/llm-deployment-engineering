---
id: T14
title: "压测工具工程记录：llama-bench、vLLM bench与EvalScope"
type: tutorial
volume: book
layer: 0
platform: "general"
device: "general"
status: historical
source_ids: [R48, R49]
updated: 2026-10-19
summary: "技术标签：engine / HTTP / fixed load / raw results"
---

# 压测工具工程记录：llama-bench、vLLM bench与EvalScope

[工程实例索引](../cases/README.md) · [知识体系总目录](../SUMMARY.md)

技术标签：`engine / HTTP / fixed load / raw results`

## 工程边界

| 工具 | 测量对象 | 必须固定 |
| --- | --- | --- |
| llama-bench | 引擎pp/tg | build、模型、后端、层数、线程、pp/tg和重复数 |
| vLLM bench serve | 服务端HTTP请求 | tokenizer、端点、输入输出、并发/到达率、缓存和实际token |
| EvalScope | 接口负载与分组报告 | API类型、数据集、number、parallel、采样和原始明细 |
| Locust/wrk/hey | HTTP压力与应用流程 | 自定义SSE/结束语义；普通req/s不代替token/s |

下方完整保留作者的工具说明、安装、命令和输出字段；涉及当前设备与框架的命令仍需固定到实际版本。统一统计定义与异常样例见[性能测试专题](../chapters/performance/benchmarking.md)。

## 完整技术记录的使用约定

以下直接保留相关FlowUs文章的技术正文、命令、表格、日志、失败和后续实验，不以摘要替代原过程。私人路径、节点、认证与附件地址脱敏；`<NODE_IP>`等占位符需要按当前环境填写。原建议或预测仍是建议或预测。上方执行顺序与技术修订用于解释历史记录中的冲突，历史GPU/NPU实验未在本轮重跑。

## 证据

- [R48 完整技术正文](../evidence/sources/R48.md)
- [R49 完整技术正文](../evidence/sources/R49.md)
