# 知识体系图片

[返回总目录](../README.md)

## 1. 按部署顺序重绘的阅读路线

- [deployment-workflow.png](deployment-workflow.png)：1440 × 940，正文与首页使用的阅读路线图。
- [deployment-workflow.svg](deployment-workflow.svg)：同内容矢量图，可放大查看。
- 生成脚本：[render_deployment_workflow.py](../../../tools/render_deployment_workflow.py)。

图中四个阶段对应 01～13 章，作用是帮助定位操作顺序。它是学习路线，不是运行截图或硬件支持矩阵。

在仓库根目录生成，需要 Python、Pillow 和中文字体：

```bash
python -m pip install Pillow==12.1.1
python tools/render_deployment_workflow.py
```

脚本查找 Windows 微软雅黑或 Linux Noto Sans CJK；字体未随仓库分发。没有字体时可在脚本 `candidates` 中指定本机字体。PNG 已渲染为像素，SVG 使用查看设备的字体。

## 2. 作者提供的原始完整框架图

- [edge-llm-deployment-framework-original.png](edge-llm-deployment-framework-original.png)：1536 × 1024，原图保留原样。
- SHA256：`3a4f599b7d7fd71cbf286153c891eb7c8dfb72a55cf25e17da69afc4fedd7f80`。
- 用途：对照“一条主线、五层能力、七个模块”和工程闭环。

原图表达知识范围。GGUF/AWQ/GPTQ 分类、框架定位和性能指标口径等按[第 13 章修订](../13-glossary-and-references.md)理解。原稿的临时签名图片地址没有纳入仓库。

## 3. 早期简图

[deployment-engineering-map.png](deployment-engineering-map.png)与[deployment-engineering-map.svg](deployment-engineering-map.svg)是早期概括版，保留供历史对照。当前阅读入口使用新的 `deployment-workflow` 图片。

早期简图由[原脚本](../../../tools/render_knowledge_map.py)生成，执行方式与字体选项见该脚本；不用于重建作者提供的原图。

## 4. 操作与结果截图

正文引用[原有 A10 Case](../../../cases/llama-cpp-flash-attention/CASE.md)中的真实截图。为减少阅读时的大片空白，[screenshots/](screenshots/)保存 8 张阅读节选：保留完整宽度与上方 480 像素，只去掉输出下方空白，保留应用、命令与完整结果。每处图注均提供完整原图链接，Case 中的图片未修改。

在仓库根目录生成节选：

```bash
python tools/render_evidence_excerpts.py
```

坐标固定为 `(0, 0, 1247, 480)`。脚本检查原图数量和尺寸，原图变化后需要重新检查裁剪范围。节选不重绘、不替换文字、不生成新的运行结果。

新绘制的路线图没有冒充运行证据；其他平台未取得可公开原始截图时，使用有来源和边界说明的技术转录。
