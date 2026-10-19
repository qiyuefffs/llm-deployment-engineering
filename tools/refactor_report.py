"""Write the refactor comparison report from the saved baseline and current book."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import validate_book


ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / "docs/01-deployment-foundations"
BASELINE = ROOT / "reports/baseline.json"


def main() -> None:
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    html = (BOOK / "book.html").read_text(encoding="utf-8")
    match = validate_book.BOOK_DATA.search(html)
    if not match:
        raise ValueError("book.html has no search data; build it before generating the report")
    data = json.loads(match.group("data"))
    issues = validate_book.collect_issues()
    errors = [issue for issue in issues if issue.level == "ERROR"]
    warnings = [issue for issue in issues if issue.level == "WARN"]
    volumes = {"book": 0, "cases": 0, "evidence": 0}
    for chapter in data["chapters"]:
        volumes[chapter["volume"]] += 1
    markdown = list(BOOK.rglob("*.md"))
    r_sources = list((BOOK / "evidence/sources").glob("R[0-9][0-9].md"))
    hashes = json.loads((ROOT / "reports/evidence-hashes.json").read_text(encoding="utf-8"))
    ledger = json.loads((ROOT / "reports/evidence-sanitization.json").read_text(encoding="utf-8"))
    unchanged = sanitized = 0
    for path in r_sources:
        source_id, body = validate_book.evidence_body(path)
        actual = hashlib.sha256(body.encode("utf-8")).hexdigest()
        original = hashes.get(source_id, {}).get("body_sha256")
        if actual == original:
            unchanged += 1
        elif source_id in ledger:
            record = ledger[source_id]
            if record.get("original_body_sha256") == original and record.get("sanitized_body_sha256") == actual:
                sanitized += 1
    snapshots = json.loads((ROOT / "reports/project-evidence.json").read_text(encoding="utf-8"))
    valid_snapshots = sum(
        (ROOT / record["path"]).is_file()
        and hashlib.sha256((ROOT / record["path"]).read_bytes()).hexdigest() == record["snapshot_sha256"]
        for record in snapshots
    )
    cases = [path for path in (BOOK / "cases").glob("C*/README.md")]
    complete_cases = 0
    for path in cases:
        headings = {
            heading.group("title").strip()
            for heading in validate_book.HEADING.finditer(validate_book.visible(path.read_text(encoding="utf-8")))
        }
        complete_cases += set(validate_book.CASE_SECTIONS).issubset(headings)
    projects = sorted((BOOK / "engineering/projects").glob("[0-9][0-9]-*.md"))
    book_bytes = (BOOK / "book.html").stat().st_size
    browser_path = ROOT / "reports/offline-browser-check.json"
    browser = json.loads(browser_path.read_text(encoding="utf-8")) if browser_path.is_file() else {}
    browser_current = browser.get("book_sha256") == hashlib.sha256((BOOK / "book.html").read_bytes()).hexdigest()
    index_bytes = len(match.group("data").encode("utf-8"))
    embedded = sum(
        len(value)
        for value in re.findall(r"data:image/[^;]+;base64,([A-Za-z0-9+/=]+)", html)
    )
    lines = [
        "# 三卷重构报告",
        "",
        "本报告对比冻结的迁移前基线（`reports/baseline.json`）与当前离线书。统计与验收结果在生成时读取实际文件；三卷架构与每个项目独立成章的组织方式保持不变。",
        "",
        "## 结构",
        "",
        "| 项目 | 迁移前 | 当前 |",
        "| --- | ---: | ---: |",
        f"| Markdown 文档 | {baseline['records']} | {len(markdown)} |",
        f"| 离线书章节 | 59 | {len(data['chapters'])} |",
        f"| R 原文 | 50（混在实例页） | {len(r_sources)}（独立证据页） |",
        f"| 教程卷章节 | 未分卷 | {volumes['book']} |",
        f"| 实例卷章节 | 未分卷 | {volumes['cases']} |",
        f"| 证据卷章节 | 未分卷 | {volumes['evidence']} |",
        f"| 独立项目文档 | 未单列 | {len(projects)} |",
        f"| 项目原文脱敏快照 | 未归档 | {len(snapshots)} |",
        "",
        "## 离线书",
        "",
        "| 指标 | 迁移前 | 当前 |",
        "| --- | ---: | ---: |",
        f"| `book.html` | {baseline['html']['book_html_bytes']:,} 字节 | {book_bytes:,} 字节 |",
        f"| 搜索索引 | {baseline['html']['search_index_bytes']:,} 字节 | {index_bytes:,} 字节 |",
        f"| 内嵌图片 base64 | {baseline['html']['embedded_image_base64_bytes']:,} 字节 | {embedded:,} 字节 |",
        f"| 小节级搜索记录 | 章级 | {len(data['sections'])} 条 |",
        "",
        "## 验收",
        "",
        f"- `python tools/validate_book.py`：{len(errors)} errors，{len(warnings)} warnings。",
        f"- R 正文：{unchanged} 份与迁移前基线相同，{sanitized} 份通过脱敏前后双重校验；合计 {unchanged + sanitized}/{len(hashes)}。冻结的原始基线未覆盖。",
        f"- 项目原文快照：{valid_snapshots}/{len(snapshots)} 通过清单 SHA-256 校验。",
        f"- 设备实例模板：{complete_cases}/{len(cases)} 包含结论、适用边界、环境与制品、执行路径、结果、失败与修订、证据、未验证八节。",
        f"- 内部 Markdown 链接：中文书、英文文档和仓库中英文入口共 {sum(issue.message.startswith(('链接目标不存在', '锚点不存在')) for issue in errors)} 个失效目标或锚点。",
        f"- 体积预算：离线书 {'通过' if book_bytes <= 3_200_000 else '未通过'} 3.2MB 上限；索引 {'通过' if index_bytes <= 200_000 else '未通过'} 200KB 上限。搜索预览缩短不删减正文。",
        "- 隐私扫描覆盖中文与英文文档、离线书、结构化结果及报告；哈希记录只保存摘要，不保存被替换的身份或凭据值。扫描规则不代替人工核对。",
        "",
        "## 本轮内容恢复",
        "",
        "- 补回 MiniMax-M2.7、GLM-5.3-Flash、vLLM ROCm、MiniMax-H3 和 Qwen-Image 2.1 的实际环境、制品、命令、检查点、测试矩阵、计时复算、结果与失败；保留原有三篇详细项目文档。",
        "- 总方法论围绕环境准入、真实生成、实际 token、SSE 与引擎计时、冷暖与缓存、消融、多机与并发、资源和质量组织，每种方法链接具体项目或实例。",
        "- 设备实例补回代表性命令、参数和结果解释；MUSA 仍为待执行计划，音频质量失败、编译超时和未知数据继续保留。",
        "- E21–E32 保存补充项目原文，区分本机报告、随制品的作者说明和部署测试方案；私人路径、节点、登录身份、认证和模型摘要按占位符处理。",
        "",
        "## 证据边界",
        "",
        "- GLM 的性能、质量和驱动故障来自制品作者，未发现本机独立实测；新版 BALANCED 质量回退仍保留。",
        "- MiniMax 三机 benchmark 历史摘要本轮未找回原始逐轮记录，单列待回链；两份双机运行不拼接为同一配置。",
        "- Flash、TP1/TP2、MTP 与其他多变量实验仅按原始条件解释，不把配置组合收益归因给单一开关。",
        "- 本轮只整理已有记录并验证文档与离线构建，没有重新运行模型或 GPU 性能测试。",
        "",
        "## 保留事项",
        "",
        "- E01–E20 仍以合并来源页保存，未拆成 20 个独立文件。",
        "- 英文版尚未同步本轮中文扩写，通过入口链接到中文三卷结构。",
        "",
    ]
    if issues:
        lines.extend(["## 检查输出", ""])
        lines.extend(f"- {issue.level} `{issue.path}`：{issue.message}" for issue in issues)
        lines.append("")
    if browser_current and browser.get("status") == "passed":
        checks = browser["checks"]
        lines.extend([
            "## 浏览器检查",
            "",
            f"- `{browser['browser']}` 已检查与当前 HTML 摘要一致的构建；桌面 1440×1000、手机 390×844。",
            f"- {len(checks['independent_project_chapters'])} 个项目逐章显示，搜索高亮、多关键词、结果跳转、移动目录和首页图片均通过。",
            f"- 重复 ID {checks['structure']['duplicateIds']} 个、失效内部锚点 {checks['structure']['missingAnchors']} 个、脚本异常 {checks['runtime_errors']} 个、外部网络请求 {checks['external_network_requests']} 个。",
            "- 结构化检查记录见 `reports/offline-browser-check.json`；这些是文档阅读检查，不是模型性能复测。",
            "",
        ])
    else:
        lines.extend(["## 浏览器检查", "", "当前 HTML 构建尚无摘要匹配的浏览器检查记录。", ""])
    output = ROOT / "reports/refactor-report.md"
    output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {output.relative_to(ROOT)}")
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
