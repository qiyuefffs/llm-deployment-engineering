# 知识地图素材

- `deployment-engineering-map.png`：1680 × 1352，供 Markdown、笔记和演示直接使用。
- `deployment-engineering-map.svg`：保留可编辑文字和形状，适合缩放与二次编辑。
- 来源：依据用户提供的旧知识图重新整理和绘制；并非性能结果或操作截图。

内容取舍见上一层章节的“这次相对旧图改了什么”。图中不列完整的硬件支持矩阵和具体参数默认值，避免版本更新后产生错误承诺。

在仓库根目录执行下面的命令可以重建两种文件（不需要 GPU）：

```bash
python -m pip install Pillow==12.1.1
python tools/render_knowledge_map.py
```

需安装中文字体。脚本在 Windows 查找微软雅黑，在 Linux 查找 Noto Sans CJK，在 macOS 查找苹方；也可以显式传入 `--font /path/to/chinese-font.ttc --font-bold /path/to/chinese-bold-font.ttc`。字体未随仓库分发。SVG 的文本显示会使用查看设备上的可用字体；PNG 已将文字渲染为像素，不依赖读者安装字体。
