"""Validate volume boundaries, evidence hashes, links, and offline-book budgets."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / "docs/01-deployment-foundations"
REPORTS = ROOT / "reports"
SUMMARY_LINK = re.compile(r"^\s*- \[[^]]+]\((?P<path>[^)#]+\.md)\)", re.MULTILINE)
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^]]+]\((?P<target>[^)]+)\)")
HEADING = re.compile(r"^(?P<level>#{1,6})\s+(?P<title>.+?)\s*$", re.MULTILINE)
CODE_FENCE = re.compile(r"```[^\n]*\n.*?```", re.DOTALL)
BOOK_DATA = re.compile(
    r'<script id="book-data" type="application/json">(?P<data>.*?)</script>', re.DOTALL
)
REQUIRED_FRONT_MATTER = {
    "id",
    "title",
    "type",
    "volume",
    "layer",
    "platform",
    "device",
    "status",
    "source_ids",
    "updated",
    "summary",
}
CASE_SECTIONS = (
    "结论",
    "适用边界",
    "环境与制品",
    "执行路径",
    "结果",
    "失败与修订",
    "证据",
    "未验证",
)


@dataclass
class Issue:
    level: str
    path: str
    message: str


def parse_front_matter(text: str) -> tuple[dict[str, object], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text
    data: dict[str, object] = {}
    for line in text[4:end].splitlines():
        if not line or line.startswith((" ", "\t")) or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            data[key] = [item.strip() for item in value[1:-1].split(",") if item.strip()]
        elif value.isdigit():
            data[key] = int(value)
        else:
            data[key] = value.strip("\"'")
    return data, text[end + 5 :]


def slug(text: str) -> str:
    text = re.sub(r"<[^>]*>", "", text)
    text = text.replace("`", "").replace("*", "").lower()
    return re.sub(r"[^\w\-\s]", "", text, flags=re.UNICODE).replace(" ", "-")


def anchors(text: str) -> set[str]:
    result = set()
    counts: dict[str, int] = {}
    for match in HEADING.finditer(visible(text)):
        key = slug(match.group("title"))
        count = counts.get(key, 0)
        counts[key] = count + 1
        result.add(key if count == 0 else f"{key}-{count}")
    return result


def visible(text: str) -> str:
    return CODE_FENCE.sub("", parse_front_matter(text)[1])


def evidence_body(path: Path) -> tuple[str, str]:
    _, body = parse_front_matter(path.read_text(encoding="utf-8"))
    lines = body.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if re.match(r"^# R\d{2}\s+·\s+", line):
            return re.match(r"^# (R\d{2})", line).group(1), "".join(lines[index + 1 :])
    return "", body


def check_volume_summary(issues: list[Issue]) -> set[Path]:
    summary = (BOOK / "SUMMARY.md").read_text(encoding="utf-8")
    paths = set()
    for match in SUMMARY_LINK.finditer(summary):
        path = (BOOK / match.group("path")).resolve()
        paths.add(path)
        if not path.is_file():
            issues.append(Issue("ERROR", "SUMMARY.md", f"目录文件不存在：{match.group('path')}"))
    for volume in ("cases", "evidence"):
        if not (BOOK / volume).is_dir():
            issues.append(Issue("ERROR", "SUMMARY.md", f"缺少 {volume} 卷目录"))
        if not any(path.is_relative_to((BOOK / volume).resolve()) for path in paths):
            issues.append(Issue("WARN", "SUMMARY.md", f"目录未列出 {volume} 卷章节"))
    return paths


def check_documents(issues: list[Issue]) -> None:
    ids: dict[str, Path] = {}
    source_ids = {f"R{index:02}" for index in range(1, 51)}
    evidence_records = BOOK / "evidence/records/README.md"
    if evidence_records.is_file():
        source_ids.update(re.findall(r"\bE\d{2}\b", evidence_records.read_text(encoding="utf-8")))
    else:
        source_ids.update(f"E{index:02}" for index in range(1, 21))
    for path in (BOOK / "evidence/records").glob("E[0-9][0-9].md"):
        front, _ = parse_front_matter(path.read_text(encoding="utf-8"))
        source_ids.add(str(front.get("id", "")))
    for path in sorted(BOOK.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(BOOK).as_posix()
        front, _ = parse_front_matter(text)
        missing = REQUIRED_FRONT_MATTER - set(front)
        if missing:
            issues.append(Issue("ERROR", relative, f"front matter 缺字段：{', '.join(sorted(missing))}"))
            continue
        chapter_id = str(front["id"])
        if chapter_id in ids:
            issues.append(
                Issue("ERROR", relative, f"ID {chapter_id} 与 {ids[chapter_id].relative_to(BOOK)} 重复")
            )
        ids[chapter_id] = path
        declared_sources = front.get("source_ids", [])
        if isinstance(declared_sources, str):
            declared_sources = [declared_sources] if declared_sources else []
        unknown = [item for item in declared_sources if item not in source_ids]
        if unknown:
            issues.append(Issue("ERROR", relative, f"source_ids 不存在：{', '.join(unknown)}"))
        if front["type"] == "case" and chapter_id != "C00":
            headings = {match.group("title").strip() for match in HEADING.finditer(visible(text))}
            missing_sections = [section for section in CASE_SECTIONS if section not in headings]
            if missing_sections:
                issues.append(
                    Issue("WARN", relative, f"实例章缺模板小节：{', '.join(missing_sections)}")
                )


def check_evidence_hashes(issues: list[Issue]) -> None:
    baseline_path = REPORTS / "evidence-hashes.json"
    if not baseline_path.is_file():
        issues.append(Issue("ERROR", "reports/evidence-hashes.json", "缺少迁移前证据哈希基线"))
        return
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    sanitization_path = REPORTS / "evidence-sanitization.json"
    sanitization = (
        json.loads(sanitization_path.read_text(encoding="utf-8"))
        if sanitization_path.is_file()
        else {}
    )
    found: dict[str, Path] = {}
    for path in sorted((BOOK / "evidence/sources").glob("R[0-9][0-9].md")):
        source_id, body = evidence_body(path)
        if not source_id:
            issues.append(Issue("ERROR", path.relative_to(BOOK).as_posix(), "缺少 Rxx H1"))
            continue
        found[source_id] = path
        expected = baseline.get(source_id, {}).get("body_sha256")
        if source_id in sanitization:
            record = sanitization[source_id]
            if record.get("original_body_sha256") != expected:
                issues.append(
                    Issue("ERROR", path.relative_to(BOOK).as_posix(), f"{source_id} 脱敏前摘要未对应迁移基线")
                )
            expected = record.get("sanitized_body_sha256")
        actual = hashlib.sha256(body.encode("utf-8")).hexdigest()
        if actual != expected:
            issues.append(
                Issue("ERROR", path.relative_to(BOOK).as_posix(), f"{source_id} 正文哈希与迁移/脱敏记录不一致")
            )
    missing = sorted(set(baseline) - set(found))
    if missing:
        issues.append(Issue("ERROR", "evidence/sources", f"缺少来源：{', '.join(missing)}"))


def check_project_snapshots(issues: list[Issue]) -> None:
    manifest_path = REPORTS / "project-evidence.json"
    if not manifest_path.is_file():
        return
    for record in json.loads(manifest_path.read_text(encoding="utf-8")):
        path = ROOT / record["path"]
        if not path.is_file():
            issues.append(Issue("ERROR", record["path"], "项目证据快照不存在"))
        elif hashlib.sha256(path.read_bytes()).hexdigest() != record["snapshot_sha256"]:
            issues.append(Issue("ERROR", record["path"], "项目证据快照与脱敏后清单不一致"))


def check_private_identifiers(issues: list[Issue]) -> None:
    patterns = {
        "私人用户目录": re.compile(r"/home/[A-Za-z0-9_.-]+/|/Users/[A-Za-z0-9_.-]+/"),
        "私人存储卷": re.compile(r"/Volumes/[^/\s`\"<>]+"),
        "私网节点地址": re.compile(r"\b192\.168\.\d{1,3}\.\d{1,3}\b"),
        "未脱敏的登录身份": re.compile(r"\b[A-Za-z0-9_.-]+@<NODE_IP>"),
        "未脱敏的认证示例": re.compile(
            r"(?:当前实际 API Key：|The current actual API Key:)\s*```[^\n]*\n(?![ \t]*<)[^\n]+",
            re.IGNORECASE,
        ),
        "未脱敏的认证排障说明": re.compile(
            r"(?:请求头里的 key 不对。当前应使用 |The key in the request.s head is wrong\. Currently used )`(?!<)[^`]+`",
            re.IGNORECASE,
        ),
    }
    public_paths = {ROOT / "README.md", ROOT / "README.en.md"}
    for directory in (ROOT / "docs", ROOT / "cases", REPORTS):
        public_paths.update(
            path for path in directory.rglob("*")
            if path.suffix in {".md", ".json", ".jsonl", ".txt", ".log", ".html"}
        )
    for path in sorted(public_paths):
        text = path.read_text(encoding="utf-8")
        for label, pattern in patterns.items():
            if pattern.search(text):
                issues.append(Issue("ERROR", path.relative_to(ROOT).as_posix(), f"发现{label}，请替换占位符"))


def check_links(issues: list[Issue]) -> None:
    anchor_cache: dict[Path, set[str]] = {}
    paths = set(BOOK.rglob("*.md")) | set((ROOT / "docs/en").rglob("*.md"))
    paths.update(ROOT / name for name in ("README.md", "README.en.md"))
    for path in sorted(paths):
        text = CODE_FENCE.sub("", path.read_text(encoding="utf-8"))
        relative = path.relative_to(ROOT).as_posix()
        for match in MARKDOWN_LINK.finditer(text):
            target = match.group("target").strip()
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            if target.startswith("[") and "附件地址不公开" in target:
                continue
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc:
                continue
            resolved = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path.resolve()
            if not resolved.exists():
                issues.append(Issue("ERROR", relative, f"链接目标不存在：{target}"))
                continue
            if parsed.fragment and resolved.suffix == ".md":
                if resolved not in anchor_cache:
                    anchor_cache[resolved] = anchors(resolved.read_text(encoding="utf-8"))
                if unquote(parsed.fragment) not in anchor_cache[resolved]:
                    issues.append(Issue("ERROR", relative, f"锚点不存在：{target}"))


def check_budget(issues: list[Issue]) -> None:
    book_html = BOOK / "book.html"
    if book_html.is_file():
        size = book_html.stat().st_size
        if size > 3_200_000:
            issues.append(Issue("ERROR", "book.html", f"体积 {size:,} 字节，超过 3.2MB"))
        match = BOOK_DATA.search(book_html.read_text(encoding="utf-8"))
        if not match:
            issues.append(Issue("ERROR", "book.html", "缺少小节搜索索引"))
        else:
            index_size = len(match.group("data").encode("utf-8"))
            if index_size > 200_000:
                issues.append(Issue("ERROR", "book.html", f"搜索索引 {index_size:,} 字节，超过 200KB"))
            try:
                data = json.loads(match.group("data"))
                if not data.get("chapters") or not data.get("sections"):
                    issues.append(Issue("ERROR", "book.html", "搜索索引没有章节或小节记录"))
            except json.JSONDecodeError:
                issues.append(Issue("ERROR", "book.html", "搜索索引不是有效 JSON"))
    referenced_images = set()
    for path in BOOK.rglob("*.md"):
        for match in re.finditer(r"!\[[^]]*]\((?P<target>[^)]+)\)", path.read_text(encoding="utf-8")):
            target = path.parent / unquote(urlsplit(match.group("target")).path)
            referenced_images.add(target.resolve())
    for path in BOOK.rglob("*"):
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
            size = path.stat().st_size
            if path.resolve() in referenced_images and size > 300_000:
                issues.append(
                    Issue("ERROR", path.relative_to(BOOK).as_posix(), f"图片 {size:,} 字节，超过 300KB")
                )
            elif size > 300_000:
                issues.append(
                    Issue("WARN", path.relative_to(BOOK).as_posix(), f"归档原图 {size:,} 字节，未嵌入离线书")
                )


def collect_issues(*, no_budget: bool = False) -> list[Issue]:
    issues: list[Issue] = []
    check_volume_summary(issues)
    check_documents(issues)
    check_evidence_hashes(issues)
    check_project_snapshots(issues)
    check_private_identifiers(issues)
    check_links(issues)
    if not no_budget:
        check_budget(issues)
    return issues


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-budget", action="store_true", help="skip book.html and image budgets")
    args = parser.parse_args()
    issues = collect_issues(no_budget=args.no_budget)
    errors = [issue for issue in issues if issue.level == "ERROR"]
    warnings = [issue for issue in issues if issue.level == "WARN"]
    for issue in issues:
        print(f"{issue.level:5} {issue.path}: {issue.message}")
    print(f"\n{len(errors)} errors, {len(warnings)} warnings")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
