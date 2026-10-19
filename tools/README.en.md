# Build and validate the knowledge base

[简体中文](README.md) | **English**

From the repository root, using Python 3.10 or later:

```bash
python -m pip install markdown-it-py==4.0.0
python tools/inventory.py --write
python tools/build_deployment_book.py
python tools/validate_book.py
```

The build script reads the **Chinese** [contents](../docs/01-deployment-foundations/SUMMARY.md) and generates the Chinese [book.html](../docs/01-deployment-foundations/book.html). The reader contains tutorial, case, and evidence volumes, section-level search with highlighting, and in-page navigation. `tools/validate_book.py` checks front matter, IDs, R-source hashes, links, image budgets, and the offline-book budget.

Rebuild after changing the Chinese source documents; do not edit the generated HTML directly. The frozen pre-refactor baseline remains in `reports/baseline.json`. Use `inventory.py --refresh-baseline` only when intentionally replacing that baseline. The script does not connect to FlowUs, download models, upload a website, or modify standalone cases. The browser loads no CDN or external fonts.

The [English edition](../docs/en/README.md) is available as Markdown with its own [contents](../docs/en/SUMMARY.md). The current build command does not generate an English offline reader.
