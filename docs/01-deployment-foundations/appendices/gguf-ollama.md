---
id: T16
title: "模型制品工程记录：HF转换GGUF、量化与Ollama导入"
type: tutorial
volume: book
layer: 0
platform: "general"
device: "general"
status: historical
source_ids: [R50]
updated: 2026-10-19
summary: "技术标签：safetensors / GGUF / quantize / Modelfile"
---

# 模型制品工程记录：HF转换GGUF、量化与Ollama导入

[工程实例索引](../cases/README.md) · [知识体系总目录](../SUMMARY.md)

技术标签：`safetensors / GGUF / quantize / Modelfile`

## 制品链路

```text
HF高精度源目录＋revision → 转换器commit → F16/BF16 GGUF
 → Q4/Q5/Q8候选 → llama.cpp加载与质量 → Modelfile → Ollama API
```

转换、量化、导入是三个独立检查点。GGUF不等于量化；模型磁盘分片不等于GPU切分；导入Ollama成功后还需检查模板和实际GPU卸载。完整原转换和Modelfile操作保留如下，配套统一目录示例见[GGUF制品流程](../chapters/models/gguf-conversion.md)。

## 完整技术记录的使用约定

以下直接保留相关FlowUs文章的技术正文、命令、表格、日志、失败和后续实验，不以摘要替代原过程。私人路径、节点、认证与附件地址脱敏；`<NODE_IP>`等占位符需要按当前环境填写。原建议或预测仍是建议或预测。上方执行顺序与技术修订用于解释历史记录中的冲突，历史GPU/NPU实验未在本轮重跑。

## 证据

- [R50 完整技术正文](../evidence/sources/R50.md)
