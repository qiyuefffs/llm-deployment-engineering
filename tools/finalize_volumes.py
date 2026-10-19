"""Finish volume migration after the partial file move and regenerate indexes."""

from __future__ import annotations

import json
import os
from pathlib import Path

from migrate_volumes import (
    BOOK,
    CASES,
    DIR_MOVES,
    EXTRA_MOVES,
    REPORTS,
    build_summary,
    evidence_links,
    first_heading,
    first_paragraph,
    front_matter,
    infer_layer,
    infer_platform,
    infer_status,
    read_summary_entries,
    rewrite_links,
    source_ids,
)


def main() -> None:
    baseline = json.loads((REPORTS / "evidence-hashes.json").read_text(encoding="utf-8"))
    file_map: dict[Path, Path] = {}
    dir_map: dict[Path, Path] = {}
    old_path_by_new: dict[Path, Path] = {}

    for case in CASES:
        old = (BOOK / case.source).resolve()
        new = (BOOK / case.target).resolve()
        file_map[old] = new
        old_path_by_new[new] = old
    for old_relative, new_relative in EXTRA_MOVES.items():
        old = (BOOK / old_relative).resolve()
        new = (BOOK / new_relative).resolve()
        file_map[old] = new
        old_path_by_new[new] = old
    file_map[(BOOK / "engineering/README.md").resolve()] = (BOOK / "cases/README.md").resolve()
    for old_relative, new_relative in DIR_MOVES.items():
        old_dir = (BOOK / old_relative).resolve()
        new_dir = (BOOK / new_relative).resolve()
        dir_map[old_dir] = new_dir
        for path in new_dir.rglob("*"):
            if path.is_file():
                old_path_by_new[path.resolve()] = old_dir / path.relative_to(new_dir)

    for path in sorted(BOOK.rglob("*.md")):
        if path.parent == BOOK / "evidence/sources" and path.name.startswith("R") and path.name != "README.md":
            continue
        old_source = old_path_by_new.get(path.resolve(), path.resolve())
        text = path.read_text(encoding="utf-8")
        path.write_text(
            rewrite_links(text, old_source, path.resolve(), file_map, dir_map),
            encoding="utf-8",
        )
    for path in (BOOK / "cases").glob("C*/README.md"):
        text = path.read_text(encoding="utf-8")
        path.write_text(
            text.replace("../../../evidence/sources/", "../../evidence/sources/"),
            encoding="utf-8",
        )

    source_titles = {
        source_id: str(metadata["title"])
        for source_id, metadata in baseline.items()
    }
    sources_dir = BOOK / "evidence/sources"
    source_index = [
        "---",
        "id: R00",
        'title: "R01–R50 原文索引"',
        "type: evidence",
        "volume: evidence",
        "layer: 0",
        'platform: "general"',
        'device: "general"',
        "status: historical",
        "source_ids: [R01, R50]",
        "updated: 2026-10-19",
        'summary: "按编号进入 50 份完整技术记录与原始测量条件。"',
        "---",
        "",
        "# R01–R50 原文索引",
        "",
        "本卷正文由迁移前 Markdown 原样抽出，仅调整标题层级与路径。每个文件的正文 SHA-256 由 `tools/validate_book.py` 对照迁移基线检查。",
        "",
        "| 编号 | 标题 | 原实例 |",
        "| --- | --- | --- |",
    ]
    source_case = {case.source: case.case_id for case in CASES}
    for source_id in sorted(source_titles):
        source_index.append(
            f"| [{source_id}]({source_id}.md) | {source_titles[source_id]} | "
            f"{source_case.get(str(baseline[source_id]['source']), '证据附录')} |"
        )
    source_index.append("")
    (sources_dir / "README.md").write_text("\n".join(source_index), encoding="utf-8")

    case_index = [
        "---",
        "id: C00",
        'title: "实例卷索引"',
        "type: case",
        "volume: cases",
        "layer: 1",
        'platform: "multi-platform"',
        'device: "multiple devices"',
        "status: historical",
        "source_ids: [R01, R50]",
        "updated: 2026-10-19",
        'summary: "按设备进入十四个实例入口，并跳转到对应证据正文。"',
        "---",
        "",
        "# 实例卷索引",
        "",
        "实例页保留适用范围、执行顺序、结果解释与证据入口；完整原始记录按编号存入证据卷。",
        "",
        "| 实例 | 平台 | 设备 | 来源 | 入口 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for case in CASES:
        ids = sorted(
            source_id
            for source_id, metadata in baseline.items()
            if metadata["source"] == case.source
        )
        case_index.append(
            f"| {case.case_id} | {case.platform} | {case.device} | {', '.join(ids) or '无 R 原文'} | "
            f"[{case.target.removeprefix('cases/')}]({case.target.removeprefix('cases/')}) |"
        )
    case_index.append("")
    (BOOK / "cases/README.md").write_text("\n".join(case_index), encoding="utf-8")

    evidence_index = [
        "---",
        "id: EV00",
        'title: "证据卷阅读说明"',
        "type: evidence",
        "volume: evidence",
        "layer: 0",
        'platform: "general"',
        'device: "general"',
        "status: historical",
        "source_ids: [R01, R50, E01, E20]",
        "updated: 2026-10-19",
        'summary: "先读证据边界，再进入 R 原文、E 记录和结构化测量文件。"',
        "---",
        "",
        "# 证据卷阅读说明",
        "",
        "- [工程来源、E01–E20 与测量边界](records/README.md)",
        "- [R01–R50 原文索引](sources/README.md)",
        "- [结构化测量文件](measurements.json)",
        "- [来源覆盖清单](source-coverage.json)",
        "",
        "证据卷不以摘要替代原始过程。实例页中的结论必须能回到 R/E 编号或结构化测量字段。",
        "",
    ]
    (BOOK / "evidence/README.md").write_text("\n".join(evidence_index), encoding="utf-8")

    old_entries = read_summary_entries()
    (BOOK / "SUMMARY.md").write_text(
        build_summary(old_entries, file_map, source_titles),
        encoding="utf-8",
    )

    fixed_ids = {
        "cases/README.md": "C00",
        "evidence/README.md": "EV00",
        "evidence/records/README.md": "E00",
        "evidence/sources/README.md": "R00",
    }
    for case in CASES:
        fixed_ids[case.target] = case.case_id
    for source_id in source_titles:
        fixed_ids[f"evidence/sources/{source_id}.md"] = source_id
    counters = {"book": 0, "cases": 0, "evidence": 0}
    used_ids = set(fixed_ids.values())
    for path in sorted(BOOK.rglob("*.md")):
        relative = path.relative_to(BOOK).as_posix()
        text = path.read_text(encoding="utf-8")
        if text.startswith("---\n"):
            continue
        title = first_heading(text)
        volume = "cases" if relative.startswith("cases/") else ("evidence" if relative.startswith("evidence/") else "book")
        kind = "case" if volume == "cases" else ("evidence" if volume == "evidence" else "tutorial")
        chapter_id = fixed_ids.get(relative)
        if chapter_id is None:
            prefix = {"book": "T", "cases": "C", "evidence": "EV"}[volume]
            while True:
                chapter_id = f"{prefix}{counters[volume]:02}"
                counters[volume] += 1
                if chapter_id not in used_ids:
                    break
        used_ids.add(chapter_id)
        case = next((item for item in CASES if item.target == relative), None)
        path.write_text(
            front_matter(
                chapter_id,
                title,
                kind,
                volume,
                case.layer if case else infer_layer(relative, title),
                case.platform if case else infer_platform(relative, title),
                case.device if case else "general",
                case.status if case else infer_status(relative, title),
                source_ids(text),
                first_paragraph(text),
            )
            + text.lstrip(),
            encoding="utf-8",
        )

    report = {
        "tutorial_documents": len([path for path in BOOK.rglob("*.md") if "cases" not in path.parts and "evidence" not in path.parts]),
        "cases": len(CASES),
        "r_sources": len(list(sources_dir.glob("R[0-9][0-9].md"))),
        "evidence_hash_baseline": len(baseline),
    }
    (REPORTS / "migration-summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
