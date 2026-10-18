# 知识体系阅读版构建

在仓库根目录执行，Python3.10及以上：

```bash
python -m pip install markdown-it-py==4.0.0
python tools/build_deployment_book.py
```

入口是[知识体系目录](../docs/01-deployment-foundations/SUMMARY.md)，构建器按目录读取Markdown，生成[book.html](../docs/01-deployment-foundations/book.html)，保留该文件名兼容已有地址。框架、设备实例、完整技术记录、侧栏、全文搜索和图片嵌在单文件中，下载后可离线检索。代码、JSON和日志仍是仓库中的独立文件，这类链接指向GitHub。首页直接显示原始框架图。

修改正文后重新构建；不要手工编辑生成的HTML。脚本不连接FlowUs、不下载模型、不上传网站，也不改动独立Case。构建只依赖markdown-it-py及其安装依赖，浏览器端不加载CDN或外部字体。
