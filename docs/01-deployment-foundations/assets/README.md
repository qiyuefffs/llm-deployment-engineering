# 知识体系图片

## 原始完整框架图

- `edge-llm-deployment-framework-original.png`：1536 × 1024，作者本次提供的原图，已原样纳入知识体系和仓库首页。
- 图名：大模型部署适配知识体系框架。
- 用途：对照“一条主线、五层能力、七个模块”及工程闭环，支持下载放大阅读。
- SHA256：`3a4f599b7d7fd71cbf286153c891eb7c8dfb72a55cf25e17da69afc4fedd7f80`。

它是知识概念图，不是操作截图、性能报告或已验证的硬件支持矩阵。图中格式/方法分类、框架定位和指标口径按[正文修订](../13-glossary-and-references.md)理解。原稿中的临时签名图片链接没有纳入仓库，页面直接引用本地图片文件。

## 早期简图

- `deployment-engineering-map.png`：1680 × 1352，早期概括版。
- `deployment-engineering-map.svg`：早期概括版的可编辑矢量文件。

早期简图保留用于辅助阅读；本次完整原图不是由下面脚本重建的。早期简图可在仓库根目录用原有命令生成：

```bash
python -m pip install Pillow==12.1.1
python tools/render_knowledge_map.py
```

需要中文字体。原脚本会查找平台常见字体，也支持 `--font /path/to/chinese-font.ttc --font-bold /path/to/chinese-bold-font.ttc`。字体未随仓库分发。SVG 使用查看设备上的字体，PNG 已渲染为像素。
