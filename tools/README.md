# 知识体系阅读版构建

在仓库根目录执行，Python3.10及以上：

```bash
python -m pip install markdown-it-py==4.0.0
python tools/build_deployment_book.py
```

入口是[全书目录](../docs/01-deployment-foundations/SUMMARY.md)，构建器按目录读取Markdown，生成[book.html](../docs/01-deployment-foundations/book.html)。正文、侧栏、搜索数据和书中图片嵌在单文件中，下载后可离线阅读。代码、原始JSON和日志仍是仓库中的独立文件，阅读版中的这类链接指向GitHub。

修改正文后重新构建；不要手工编辑生成的HTML。脚本不连接FlowUs、不下载模型、不上传网站，也不改动独立Case。构建只依赖markdown-it-py及其安装依赖，浏览器端不加载CDN或外部字体。

`render_deployment_workflow.py`用于生成已有的五层知识示意图；本轮保留作者原始框架图。
