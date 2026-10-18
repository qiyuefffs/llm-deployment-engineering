# Build the knowledge base offline reader

[简体中文](README.md) | **English**

From the repository root, using Python 3.10 or later:

```bash
python -m pip install markdown-it-py==4.0.0
python tools/build_deployment_book.py
```

The build script reads the **Chinese** [contents](../docs/01-deployment-foundations/SUMMARY.md) and its Markdown chapters, then generates the Chinese [book.html](../docs/01-deployment-foundations/book.html). The filename remains compatible with existing links. Framework chapters, hardware examples, complete technical records, sidebar navigation, full-text search, and embedded images are bundled into one downloadable HTML file. Code, JSON, and logs remain separate repository files, linked to GitHub. The original framework diagram appears on the home page.

Rebuild after changing the Chinese source documents; do not edit the generated HTML directly. The script does not connect to FlowUs, download models, upload a website, or modify standalone cases. Its only direct dependency is markdown-it-py, plus that package's dependencies. The reader does not load a CDN or external fonts.

The [English edition](../docs/en/README.md) is available as Markdown with its own [contents](../docs/en/SUMMARY.md). The current build command does not generate an English offline reader.
