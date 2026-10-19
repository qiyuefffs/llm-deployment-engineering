# 知识体系构建与校验

在仓库根目录执行，Python3.10及以上：

```bash
python -m pip install markdown-it-py==4.0.0
python tools/inventory.py --write
python tools/build_deployment_book.py
python tools/validate_book.py
python docs/01-deployment-foundations/examples/verify_records.py
python tools/refactor_report.py
```

入口是[知识体系目录](../docs/01-deployment-foundations/SUMMARY.md)。构建器按教程卷、实例卷和证据卷读取 Markdown，生成[book.html](../docs/01-deployment-foundations/book.html)。离线书包含三卷侧栏、小节级搜索、关键词高亮、页内目录和小节跳转。

`tools/inventory.py --write`更新当前章节盘点；冻结的迁移前基线仍保存在`reports/baseline.json`。只有明确重做基线时才使用`--refresh-baseline`。`tools/validate_book.py`检查 front matter、ID、R 正文哈希及脱敏记录、项目快照、中文书与英文入口链接、隐私字段、图片和离线书体积，发现 ERROR 时返回非零。搜索索引以实际 UTF-8 字节计，不超过 200KB；缩短搜索预览不影响正文。

三卷已经建立，日常只改正文并重跑构建与校验。`book.html`是生成文件，不要手工编辑。构建器不连接FlowUs、不下载模型、不上传网站，浏览器端不加载CDN或外部字体。

## 数据迁移工具

- `tools/migrate_volumes.py`、`tools/finalize_volumes.py`：一次性三卷迁移与索引生成，已执行。
- `tools/relink_volumes.py`：迁移后修复中文书以外的相对链接。
- `tools/refactor_report.py`：根据冻结基线和当前离线书生成[重构报告](../reports/refactor-report.md)。
