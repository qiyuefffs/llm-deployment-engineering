# 知识体系图片

[返回总目录](../README.md)

## 1. 五层能力与工程主线图

- [PNG](deployment-workflow.png)：1600×1360，知识目录和仓库首页使用。
- [SVG](deployment-workflow.svg)：相同内容的矢量版。
- [生成脚本](../../../tools/render_deployment_workflow.py)：同一布局生成两种格式。

上半部分是模型到交付的工程步骤；中间五行对应第二部分五层章节；下半部分列出七个工程模块。这是知识组织图，不是硬件支持矩阵或运行截图。

从仓库根目录重新生成：

```bash
python -m pip install Pillow==12.1.1
python tools/render_deployment_workflow.py
```

脚本查找Windows微软雅黑、Linux Noto Sans CJK或macOS苹方。字体未随仓库分发；缺少字体时在脚本候选路径中指定。PNG自带像素，SVG的实际字体由查看设备提供。

## 2. 作者原始框架图

[edge-llm-deployment-framework-original.png](edge-llm-deployment-framework-original.png)，1536×1024，保留原样。

SHA256：`3a4f599b7d7fd71cbf286153c891eb7c8dfb72a55cf25e17da69afc4fedd7f80`。

原图用于对照作者的主线、层次和模块。GGUF、量化方法、设备内存、并行和指标等表达按[附录B修订](../appendices/references.md)阅读；临时签名图片链接未保留。

## 3. 工程实例的结果证明

知识体系采用部署技术笔记中的命令、数值与错误转录，统一查[来源目录](../evidence/README.md)。没有可公开原始截图的部分，不制作模拟运行截图。

本文的新图只表达知识关系，历史性能始终注明来源与条件。
