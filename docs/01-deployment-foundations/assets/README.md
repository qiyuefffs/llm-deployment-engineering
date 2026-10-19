---
id: T18
title: "知识体系图片"
type: tutorial
volume: book
layer: 0
platform: "general"
device: "general"
status: historical
source_ids: []
updated: 2026-10-19
summary: "SHA256：3a4f599b7d7fd71cbf286153c891eb7c8dfb72a55cf25e17da69afc4fedd7f80。"
---

# 知识体系图片

[返回总目录](../README.md)

## 1. 首页框架图

[framework.webp](framework.webp) 由作者提供的原图转换，保持 1536×1024 完整画面，作为中文首页和离线书的开篇图，位于标题与介绍之前。WebP 质量参数为 92，文件为 291,138 字节。

[edge-llm-deployment-framework-original.png](edge-llm-deployment-framework-original.png) 保留原样供来源核对；此前的简化图 [framework.svg](framework.svg) 仍保留在资源目录。

SHA256：`3a4f599b7d7fd71cbf286153c891eb7c8dfb72a55cf25e17da69afc4fedd7f80`。

原图用于对照作者的主线、层次和模块。GGUF、量化方法、设备内存、并行和指标等表达按[附录B修订](../appendices/references.md)阅读；临时签名图片链接未保留。

## 2. 公开视觉样例

[`vision-input/`](vision-input) 保存多模态请求使用的 [PNG 样例](vision-input/vision-card.png) 和[预期内容与 SHA256](vision-input/expected.json)。生成与请求方法见[辅助程序](../examples/make_vision_input.py)和[视觉请求程序](../examples/vision_client.py)。

## 3. 工程实例的结果证明

知识体系采用部署技术笔记中的命令、数值与错误转录，统一查[来源目录](../evidence/records/README.md)。没有可公开原始截图的部分，不制作模拟运行截图。

框架图只表达知识关系，历史性能始终注明来源与条件。独立 Case 的截图随项目保存在各自目录。
