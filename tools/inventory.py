"""Inventory the deployment book and write the pre-refactor baseline reports."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / "docs/01-deployment-foundations"
SUPPORTED_VOLUMES = ("book", "cases", "evidence")

R_HEADING = re.compile(r"^## (?P<id>R\d{2})\s+·\s+(?P<title>.+?)\s*$", re.MULTILINE)
HEADING = re.compile(r"^(?P<level>#{1,6})\s+(?P<title>.+?)\s*$", re.MULTILINE)
SUMMARY_LINK = re.compile(r"^(?P<indent>\s*)- \[(?P<label>[^]]+)]\((?P<path>[^)#]+\.md)\)", re.MULTILINE)
CODE_FENCE = re.compile(r"```[^\n]*\n.*?```", re.DOTALL)
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^]]+]\((?P<target>[^)]+)\)")
SEARCH_DATA = re.compile(
    r'<script id="book-data" type="application/json">(?P<data>.*?)</script>',
    re.DOTALL,
)


CASE_MAP = {
    "engineering/nvidia-rtx2060.md": ("C01", "cases/C01-rtx2060/README.md"),
    "engineering/nvidia-dual-gpu.md": ("C02", "cases/C02-dual-4080/README.md"),
    "engineering/nvidia-gb10.md": ("C03", "cases/C03-gb10/README.md"),
    "engineering/nvidia-gb10-multimodal.md": ("C04", "cases/C04-gb10-multimodal/README.md"),
    "engineering/amd-780m.md": ("C05", "cases/C05-radeon-780m/README.md"),
    "engineering/amd-8060s.md": ("C06", "cases/C06-radeon-8060s/README.md"),
    "engineering/amd-395-rpc.md": ("C07", "cases/C07-amd-395-rpc/README.md"),
    "engineering/amd-w7900.md": ("C08", "cases/C08-w7900/README.md"),
    "engineering/intel-arc-npu.md": ("C09", "cases/C09-intel-arc-npu/README.md"),
    "engineering/apple-metal.md": ("C10", "cases/C10-m3-metal/README.md"),
    "engineering/apple-mlx.md": ("C11", "cases/C11-m3-mlx/README.md"),
    "engineering/ascend-310p.md": ("C12", "cases/C12-ascend-310p/README.md"),
    "engineering/musa.md": ("C13", "cases/C13-musa/README.md"),
    "practice/first-service/README.md": ("C14", "cases/C14-windows-cpu/README.md"),
}


@dataclass
class Record:
    path: str
    volume: str
    chapter_id: str
    title: str
    characters: int
    prose_characters: int
    code_characters: int
    code_ratio: float
    code_blocks: int
    source_ids: list[str]


def strip_front_matter(text: str) -> str:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end >= 0:
            return text[end + 5 :]
    return text


def visible_text(text: str) -> str:
    return CODE_FENCE.sub("", strip_front_matter(text))


def first_heading(text: str) -> str:
    match = HEADING.search(visible_text(text))
    return match.group("title").strip() if match else ""


def source_ids(text: str) -> list[str]:
    ids = set(re.findall(r"\b[RE]\d{2}\b", text))
    return sorted(ids)


def markdown_stats(path: Path, volume: str, chapter_id: str) -> Record:
    text = path.read_text(encoding="utf-8")
    body = strip_front_matter(text)
    code = "\n".join(match.group(0) for match in CODE_FENCE.finditer(body))
    prose = CODE_FENCE.sub("", body)
    prose_chars = len(re.sub(r"\s+", "", prose))
    code_chars = len(re.sub(r"\s+", "", code))
    total = prose_chars + code_chars
    return Record(
        path=path.relative_to(BOOK).as_posix(),
        volume=volume,
        chapter_id=chapter_id,
        title=first_heading(text),
        characters=total,
        prose_characters=prose_chars,
        code_characters=code_chars,
        code_ratio=round(code_chars / total, 4) if total else 0.0,
        code_blocks=len(CODE_FENCE.findall(body)),
        source_ids=source_ids(body),
    )


def summary_entries() -> list[dict[str, str | int]]:
    entries: list[dict[str, str | int]] = []
    group = ""
    for line in (BOOK / "SUMMARY.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            group = line[3:].strip()
        match = SUMMARY_LINK.match(line)
        if match:
            entries.append(
                {
                    "label": match.group("label"),
                    "path": match.group("path"),
                    "group": group,
                    "depth": len(match.group("indent")) // 2,
                }
            )
    return entries


def infer_volume(relative: str) -> str:
    if relative.startswith("cases/"):
        return "cases"
    if relative.startswith("evidence/"):
        return "evidence"
    return "book"


def front_value(text: str, key: str) -> str:
    if not text.startswith("---\n"):
        return ""
    end = text.find("\n---\n", 4)
    if end < 0:
        return ""
    match = re.search(rf"^{re.escape(key)}:\s*(.+?)\s*$", text[4:end], re.MULTILINE)
    return match.group(1).strip().strip('"') if match else ""


def collect_records() -> list[Record]:
    paths = sorted(BOOK.rglob("*.md"))
    records: list[Record] = []
    ids: dict[str, str] = {}
    for index, path in enumerate(paths, 1):
        relative = path.relative_to(BOOK).as_posix()
        text = path.read_text(encoding="utf-8")
        volume = front_value(text, "volume") or infer_volume(relative)
        prefix = "T" if volume == "book" else ("C" if volume == "cases" else "E")
        ids[relative] = front_value(text, "id") or f"{prefix}{index:02}"
        records.append(markdown_stats(path, volume, ids[relative]))
    return records


def build_migration_map(records: list[Record]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    by_path = {record.path: record for record in records}
    tutorials = [record for record in records if record.volume == "book"]
    for index, record in enumerate(tutorials, 1):
        new_path = record.path
        rows.append(
            {
                "old_path": record.path,
                "new_volume": "book",
                "new_path": new_path,
                "new_id": f"T{index:02}",
            }
        )
    for old, (case_id, new_path) in CASE_MAP.items():
        record = by_path.get(old)
        rows.append(
            {
                "old_path": old,
                "new_volume": "cases",
                "new_path": new_path,
                "new_id": case_id,
            }
        )
        if record:
            rows[-1]["source_ids"] = ",".join(record.source_ids)
    for record in records:
        for source_id in record.source_ids:
            if source_id.startswith("R"):
                rows.append(
                    {
                        "old_path": f"{record.path}#{source_id}",
                        "new_volume": "evidence",
                        "new_path": f"evidence/sources/{source_id}.md",
                        "new_id": source_id,
                    }
                )
    return rows


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def evidence_hashes() -> dict[str, dict[str, object]]:
    records: dict[str, dict[str, object]] = {}
    for path in sorted(BOOK.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        matches = list(R_HEADING.finditer(text))
        for index, match in enumerate(matches):
            start = match.end() + (1 if match.end() < len(text) and text[match.end()] == "\n" else 0)
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            body = text[start:end]
            records[match.group("id")] = {
                "source": path.relative_to(BOOK).as_posix(),
                "title": match.group("title"),
                "body_sha256": sha256_bytes(body.encode("utf-8")),
                "body_characters": len(body),
            }
    return records


def link_stats() -> dict[str, int]:
    total = 0
    unresolved = 0
    external = 0
    for path in BOOK.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK.finditer(text):
            target = match.group("target").strip()
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            parsed = urlsplit(target)
            total += 1
            if parsed.scheme or parsed.netloc:
                external += 1
                continue
            if not parsed.path:
                continue
            resolved = (path.parent / unquote(parsed.path)).resolve()
            if not resolved.exists():
                unresolved += 1
    return {"total": total, "external": external, "unresolved": unresolved}


def html_baseline() -> dict[str, object]:
    path = BOOK / "book.html"
    data = path.read_bytes()
    html = data.decode("utf-8")
    match = SEARCH_DATA.search(html)
    search_bytes = len(match.group("data").encode("utf-8")) if match else 0
    embedded_images = sum(
        len(value)
        for value in re.findall(r"data:image/[^;]+;base64,([A-Za-z0-9+/=]+)", html)
    )
    return {
        "book_html_bytes": len(data),
        "search_index_bytes": search_bytes,
        "embedded_image_base64_bytes": embedded_images,
        "anchor_links": html.count('href="#'),
    }


def image_baseline() -> dict[str, object]:
    images = []
    for path in BOOK.rglob("*"):
        if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}:
            continue
        images.append(
            {
                "path": path.relative_to(BOOK).as_posix(),
                "bytes": path.stat().st_size,
            }
        )
    return {"count": len(images), "total_bytes": sum(item["bytes"] for item in images), "images": images}


def write_inventory(records: list[Record]) -> None:
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    groups: dict[str, list[Record]] = {name: [] for name in SUPPORTED_VOLUMES}
    for record in records:
        groups[record.volume].append(record)
    lines = [
        "# 章节盘点",
        "",
        "本报告由 `python tools/inventory.py --write` 生成。字符数不包含空白，代码与正文分别统计；",
        "`source_ids` 从正文中实际出现的 R/E 编号提取，不用章节标题推断。",
        "",
        "## 总量",
        "",
        f"- Markdown 文档：{len(records)}",
        f"- 正文字符：{sum(record.prose_characters for record in records):,}",
        f"- 代码字符：{sum(record.code_characters for record in records):,}",
        f"- 代码块：{sum(record.code_blocks for record in records):,}",
        f"- 唯一来源编号：{len({source for record in records for source in record.source_ids})}",
        "",
    ]
    for volume in SUPPORTED_VOLUMES:
        subset = groups[volume]
        lines.extend(
            [
                f"## {volume}",
                "",
                "| 文件 | ID | 标题 | 正文字符 | 代码字符 | 代码占比 | 来源 |",
                "| --- | --- | --- | ---: | ---: | ---: | --- |",
            ]
        )
        for record in subset:
            sources = ", ".join(record.source_ids) or "-"
            lines.append(
                f"| `{record.path}` | {record.chapter_id} | {record.title} | "
                f"{record.prose_characters:,} | {record.code_characters:,} | "
                f"{record.code_ratio:.1%} | {sources} |"
            )
        lines.append("")
    (reports / "inventory.md").write_text("\n".join(lines), encoding="utf-8")


def write_reports(records: list[Record], refresh_baseline: bool = False) -> None:
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    write_inventory(records)
    if refresh_baseline or not (reports / "migration-map.csv").exists():
        with (reports / "migration-map.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["old_path", "new_volume", "new_path", "new_id", "source_ids"],
            )
            writer.writeheader()
            for row in build_migration_map(records):
                writer.writerow({"source_ids": "", **row})
    if refresh_baseline or not (reports / "baseline.json").exists():
        hashes = evidence_hashes()
        (reports / "evidence-hashes.json").write_text(
            json.dumps(hashes, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        baseline = {
            "generated_on": "2026-10-19",
            "scope": "docs/01-deployment-foundations",
            "records": len(records),
            "prose_characters": sum(record.prose_characters for record in records),
            "code_characters": sum(record.code_characters for record in records),
            "code_blocks": sum(record.code_blocks for record in records),
            "r_sources": len(hashes),
            "links": link_stats(),
            "html": html_baseline(),
            "images": image_baseline(),
        }
        (reports / "baseline.json").write_text(
            json.dumps(baseline, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write reports/*.md,json,csv")
    parser.add_argument(
        "--refresh-baseline",
        action="store_true",
        help="replace the frozen baseline and evidence hashes with the current tree",
    )
    args = parser.parse_args()
    records = collect_records()
    if args.write:
        write_reports(records, refresh_baseline=args.refresh_baseline)
        print(f"Wrote reports for {len(records)} Markdown documents.")
        return
    print(json.dumps([asdict(record) for record in records], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
