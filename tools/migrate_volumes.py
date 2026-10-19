"""Move the existing book into tutorial, case, and evidence volumes."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / "docs/01-deployment-foundations"
REPORTS = ROOT / "reports"
R_HEADING = re.compile(r"^## (?P<id>R\d{2})\s+·\s+(?P<title>.+?)\s*$", re.MULTILINE)
H1 = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
CODE_FENCE = re.compile(r"```[^\n]*\n.*?```", re.DOTALL)
SUMMARY_LINK = re.compile(
    r"^(?P<indent>\s*)- \[(?P<label>[^]]+)]\((?P<path>[^)#]+\.md)\)",
    re.MULTILINE,
)


@dataclass(frozen=True)
class Case:
    case_id: str
    source: str
    target: str
    platform: str
    device: str
    layer: int
    status: str


CASES = (
    Case("C01", "engineering/nvidia-rtx2060.md", "cases/C01-rtx2060/README.md", "NVIDIA", "RTX 2060 12GB", 1, "historical"),
    Case("C02", "engineering/nvidia-dual-gpu.md", "cases/C02-dual-4080/README.md", "NVIDIA", "RTX 4080 dual GPU", 1, "historical"),
    Case("C03", "engineering/nvidia-gb10.md", "cases/C03-gb10/README.md", "NVIDIA", "DGX Spark / GB10", 1, "historical"),
    Case("C04", "engineering/nvidia-gb10-multimodal.md", "cases/C04-gb10-multimodal/README.md", "NVIDIA", "DGX Spark / GB10", 1, "historical"),
    Case("C05", "engineering/amd-780m.md", "cases/C05-radeon-780m/README.md", "AMD", "Radeon 780M", 1, "historical"),
    Case("C06", "engineering/amd-8060s.md", "cases/C06-radeon-8060s/README.md", "AMD", "Radeon 8060S", 1, "historical"),
    Case("C07", "engineering/amd-395-rpc.md", "cases/C07-amd-395-rpc/README.md", "AMD", "Ryzen AI Max+ 395", 1, "historical"),
    Case("C08", "engineering/amd-w7900.md", "cases/C08-w7900/README.md", "AMD", "Radeon W7900", 1, "historical"),
    Case("C09", "engineering/intel-arc-npu.md", "cases/C09-intel-arc-npu/README.md", "Intel", "Arc / NPU", 1, "historical"),
    Case("C10", "engineering/apple-metal.md", "cases/C10-m3-metal/README.md", "Apple", "M3 Ultra", 1, "historical"),
    Case("C11", "engineering/apple-mlx.md", "cases/C11-m3-mlx/README.md", "Apple", "M3 Ultra", 1, "historical"),
    Case("C12", "engineering/ascend-310p.md", "cases/C12-ascend-310p/README.md", "Ascend", "Ascend 310P3", 1, "historical"),
    Case("C13", "engineering/musa.md", "cases/C13-musa/README.md", "MUSA", "MUSA GPU (unspecified)", 1, "pending"),
    Case("C14", "practice/first-service/README.md", "cases/C14-windows-cpu/README.md", "CPU", "Windows x64 CPU", 5, "verified"),
)

EXTRA_MOVES = {
    "engineering/benchmark-tools.md": "appendices/benchmark-tools.md",
    "engineering/gguf-ollama.md": "appendices/gguf-ollama.md",
    "evidence/README.md": "evidence/records/README.md",
}

DIR_MOVES = {
    "practice/first-service": "cases/C14-windows-cpu",
}


def git_mv(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "mv", str(source), str(target)], cwd=ROOT, check=True)


def strip_front_matter(text: str) -> str:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end >= 0:
            return text[end + 5 :]
    return text


def first_heading(text: str) -> str:
    match = H1.search(CODE_FENCE.sub("", strip_front_matter(text)))
    return match.group(1).strip() if match else "未命名章节"


def source_ids(text: str) -> list[str]:
    return sorted(set(re.findall(r"\b[RE]\d{2}\b", text)))


def first_paragraph(text: str) -> str:
    body = strip_front_matter(text)
    body = body[body.find("\n", body.find("#")) + 1 :] if "#" in body else body
    for block in re.split(r"\n\s*\n", body):
        clean = block.strip()
        if not clean or clean.startswith(("#", "|", "```", "- ", ">", "[")):
            continue
        clean = re.sub(r"\[([^]]+)]\([^)]+\)", r"\1", clean)
        clean = re.sub(r"[*_`]", "", clean).replace("\n", " ")
        if clean:
            return re.sub(r"\s+", " ", clean)[:120]
    return "本章说明该主题的工程边界、执行路径和证据入口。"


def yaml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def front_matter(
    chapter_id: str,
    title: str,
    kind: str,
    volume: str,
    layer: int,
    platform: str,
    device: str,
    status: str,
    sources: list[str],
    summary: str,
) -> str:
    source_list = "[" + ", ".join(sources) + "]"
    return (
        "---\n"
        f"id: {chapter_id}\n"
        f"title: {yaml_string(title)}\n"
        f"type: {kind}\n"
        f"volume: {volume}\n"
        f"layer: {layer}\n"
        f"platform: {yaml_string(platform)}\n"
        f"device: {yaml_string(device)}\n"
        f"status: {status}\n"
        f"source_ids: {source_list}\n"
        "updated: 2026-10-19\n"
        f"summary: {yaml_string(summary)}\n"
        "---\n\n"
    )


def extract_evidence(old_path: Path) -> list[tuple[str, str, str]]:
    text = old_path.read_text(encoding="utf-8")
    matches = list(R_HEADING.finditer(text))
    extracted: list[tuple[str, str, str]] = []
    for index, match in enumerate(matches):
        start = match.end() + (1 if match.end() < len(text) and text[match.end()] == "\n" else 0)
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end]
        extracted.append((match.group("id"), match.group("title"), body))
    return extracted


def evidence_links(source_ids: list[str], target: Path) -> str:
    links = []
    for source_id in sorted(source_ids):
        evidence_target = BOOK / "evidence/sources" / f"{source_id}.md"
        relative = os.path.relpath(evidence_target, target.parent).replace(os.sep, "/")
        links.append(f"- [{source_id} 完整技术正文]({relative})")
    return "## 证据\n\n" + "\n".join(links) + "\n"


def infer_layer(relative: str, title: str) -> int:
    if relative.startswith("cases/"):
        return 1
    if "02-capability-layers/01-" in relative or "/hardware/" in relative:
        return 1
    if "02-capability-layers/02-" in relative or "/models/" in relative:
        return 2
    if "02-capability-layers/03-" in relative or "/frameworks/" in relative:
        return 3
    if "02-capability-layers/04-" in relative or "/performance/" in relative:
        return 4
    if "02-capability-layers/05-" in relative or "/delivery/" in relative:
        return 5
    if "性能" in title or "测试" in title:
        return 4
    return 0


def infer_platform(relative: str, title: str) -> str:
    probe = f"{relative} {title}".lower()
    for name in ("nvidia", "cuda", "gb10", "rtx"):
        if name in probe:
            return "NVIDIA"
    for name in ("amd", "rocm", "hip", "vulkan", "radeon"):
        if name in probe:
            return "AMD"
    for name in ("intel", "openvino", "arc", "npu"):
        if name in probe:
            return "Intel"
    for name in ("apple", "metal", "mlx", "m3"):
        if name in probe:
            return "Apple"
    if "ascend" in probe or "昇腾" in title:
        return "Ascend"
    if "musa" in probe:
        return "MUSA"
    if "cpu" in probe:
        return "CPU"
    return "general"


def infer_status(relative: str, title: str) -> str:
    if relative.startswith("cases/C13-"):
        return "pending"
    if "待验证" in title or "未验证" in title:
        return "pending"
    return "historical"


def read_summary_entries() -> list[dict[str, str | int]]:
    entries = []
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


def rewrite_links(
    text: str,
    old_source: Path,
    new_source: Path,
    file_map: dict[Path, Path],
    dir_map: dict[Path, Path],
) -> str:
    pattern = re.compile(r"(?<!!)\[([^]]+)]\(([^)]+)\)")

    def replace(match: re.Match[str]) -> str:
        label, raw_target = match.groups()
        target = raw_target.strip()
        if target.startswith("<") and target.endswith(">"):
            target = target[1:-1]
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or not parsed.path:
            return match.group(0)
        old_target = (old_source.parent / unquote(parsed.path)).resolve()
        new_target = file_map.get(old_target)
        if new_target is None:
            for old_dir, mapped_dir in dir_map.items():
                if old_target == old_dir or old_target.is_relative_to(old_dir):
                    new_target = mapped_dir / old_target.relative_to(old_dir)
                    break
        if new_target is None:
            new_target = old_target
        relative = os.path.relpath(new_target, new_source.parent).replace(os.sep, "/")
        if parsed.fragment:
            relative += "#" + parsed.fragment
        if parsed.query:
            relative += "?" + parsed.query
        return f"[{label}]({relative})"

    return pattern.sub(replace, text)


def build_summary(
    old_entries: list[dict[str, str | int]],
    file_map: dict[Path, Path],
    source_titles: dict[str, str],
) -> str:
    book: list[dict[str, str | int]] = []
    cases: list[dict[str, str | int]] = []
    evidence: list[dict[str, str | int]] = []
    seen: set[tuple[str, str]] = set()
    for entry in old_entries:
        old_target = (BOOK / str(entry["path"])).resolve()
        new_target = file_map.get(old_target, old_target)
        if not new_target.is_file():
            continue
        relative = new_target.relative_to(BOOK).as_posix()
        if relative.startswith("cases/"):
            continue
        if relative in {"evidence/records/README.md", "evidence/sources/README.md"}:
            continue
        key = (str(entry["label"]), relative)
        if key in seen or relative == "SUMMARY.md":
            continue
        seen.add(key)
        updated = dict(entry)
        updated["path"] = relative
        if relative.startswith("cases/"):
            cases.append(updated)
        elif relative.startswith("evidence/"):
            evidence.append(updated)
        else:
            book.append(updated)
    cases.sort(key=lambda item: str(item["path"]))
    evidence.sort(key=lambda item: str(item["path"]))
    lines = [
        "# 大模型部署知识体系目录",
        "",
        "全书分为教程卷、实例卷和证据卷。教程卷回答“怎样判断”，实例卷回答“具体怎样做”，证据卷保留来源、完整技术正文与测量边界。",
        "",
        "## 教程卷",
        "",
    ]
    for entry in book:
        depth = max(0, min(2, int(entry["depth"])))
        lines.append(f"{'  ' * depth}- [{entry['label']}]({entry['path']})")
    lines.extend(["", "## 实例卷", "", "- [实例卷索引](cases/README.md)"])
    for case in CASES:
        title = first_heading((BOOK / case.target).read_text(encoding="utf-8"))
        lines.append(f"- [{case.case_id} · {title}]({case.target})")
    lines.extend(
        [
            "",
            "## 证据卷",
            "",
            "- [证据卷阅读说明](evidence/README.md)",
            "- [工程来源、E01–E20 与测量边界](evidence/records/README.md)",
            "- [R01–R50 原文索引](evidence/sources/README.md)",
        ]
    )
    for source_id in sorted(source_titles):
        lines.append(f"  - [{source_id} · {source_titles[source_id]}](evidence/sources/{source_id}.md)")
    lines.extend(
        [
            "",
            "50 份源文按原章节顺序保存；路径、认证和私人节点已脱敏。历史数字保留原条件，未重跑的设备结果不包装成当前复现成绩。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    baseline = json.loads((REPORTS / "evidence-hashes.json").read_text(encoding="utf-8"))
    old_entries = read_summary_entries()
    sources_dir = BOOK / "evidence/sources"
    sources_dir.mkdir(parents=True, exist_ok=True)
    seen_sources: set[str] = set()
    source_titles: dict[str, str] = {}
    preludes: dict[str, str] = {}
    file_map: dict[Path, Path] = {}
    dir_map: dict[Path, Path] = {}

    case_sources = {case.source for case in CASES}
    for case in CASES:
        old_path = BOOK / case.source
        file_map[old_path.resolve()] = (BOOK / case.target).resolve()
    for old_relative, new_relative in EXTRA_MOVES.items():
        file_map[(BOOK / old_relative).resolve()] = (BOOK / new_relative).resolve()
    file_map[(BOOK / "engineering/README.md").resolve()] = (BOOK / "cases/README.md").resolve()
    for old_relative, new_relative in DIR_MOVES.items():
        dir_map[(BOOK / old_relative).resolve()] = (BOOK / new_relative).resolve()

    for case in CASES:
        old_path = BOOK / case.source
        text = old_path.read_text(encoding="utf-8")
        extracted = extract_evidence(old_path)
        if extracted:
            first = R_HEADING.search(text)
            preludes[case.source] = (
                text[: first.start()].rstrip()
                + "\n\n"
                + evidence_links([item[0] for item in extracted], BOOK / case.target)
                + "\n"
            )
        else:
            preludes[case.source] = text
        for source_id, title, body in extracted:
            if source_id in seen_sources:
                raise RuntimeError(f"duplicate source: {source_id}")
            seen_sources.add(source_id)
            source_titles[source_id] = title
            metadata = baseline[source_id]
            evidence_text = front_matter(
                source_id,
                f"{source_id} · {title}",
                "evidence",
                "evidence",
                0,
                case.platform,
                case.device,
                "historical",
                [source_id],
                f"完整保留 {source_id} 技术正文；只调整标题层级与路径。",
            )
            evidence_body = body[1:] if body.startswith("\n") else body
            evidence_text += f"# {source_id} · {title}\n{evidence_body}"
            target = sources_dir / f"{source_id}.md"
            target.write_text(evidence_text, encoding="utf-8")
            actual = hashlib.sha256(body.encode("utf-8")).hexdigest()
            if actual != metadata["body_sha256"]:
                raise RuntimeError(f"hash mismatch after extraction: {source_id}")

    for old_relative in EXTRA_MOVES:
        old_path = BOOK / old_relative
        text = old_path.read_text(encoding="utf-8")
        extracted = extract_evidence(old_path)
        if not extracted:
            preludes[old_relative] = text
            continue
        first = R_HEADING.search(text)
        if first is None:
            raise RuntimeError(f"no R section found in {old_relative}")
        preludes[old_relative] = (
            text[: first.start()].rstrip()
            + "\n\n"
            + evidence_links([item[0] for item in extracted], BOOK / EXTRA_MOVES[old_relative])
            + "\n"
        )
        for source_id, title, body in extracted:
            if source_id in seen_sources:
                raise RuntimeError(f"duplicate source: {source_id}")
            seen_sources.add(source_id)
            source_titles[source_id] = title
            metadata = baseline[source_id]
            evidence_text = front_matter(
                source_id,
                f"{source_id} · {title}",
                "evidence",
                "evidence",
                0,
                infer_platform(old_relative, title),
                "general",
                "historical",
                [source_id],
                f"完整保留 {source_id} 技术正文；只调整标题层级与路径。",
            )
            evidence_body = body[1:] if body.startswith("\n") else body
            evidence_text += f"# {source_id} · {title}\n{evidence_body}"
            (sources_dir / f"{source_id}.md").write_text(evidence_text, encoding="utf-8")
            actual = hashlib.sha256(body.encode("utf-8")).hexdigest()
            if actual != metadata["body_sha256"]:
                raise RuntimeError(f"hash mismatch after extraction: {source_id}")

    for old_relative in (*case_sources, *EXTRA_MOVES):
        old_path = BOOK / old_relative
        if any(old_path.is_relative_to(BOOK / directory) for directory in DIR_MOVES):
            continue
        new_relative = (
            next(case.target for case in CASES if case.source == old_relative)
            if old_relative in case_sources
            else EXTRA_MOVES[old_relative]
        )
        target = BOOK / new_relative
        if old_path.is_dir():
            raise RuntimeError(f"unexpected directory: {old_path}")
        if target.exists():
            raise RuntimeError(f"target exists: {target}")
        git_mv(old_path, target)
        matches = list(R_HEADING.finditer(preludes[old_relative]))
        if matches:
            raise RuntimeError(f"R section still present in prelude: {old_relative}")
        target.write_text(preludes[old_relative], encoding="utf-8")

    if seen_sources != {f"R{index:02}" for index in range(1, 51)}:
        raise RuntimeError(f"incomplete R sources: {sorted(seen_sources)}")

    for old_relative, new_relative in DIR_MOVES.items():
        old_dir = BOOK / old_relative
        new_dir = BOOK / new_relative
        if new_dir.exists() or not old_dir.is_dir():
            raise RuntimeError(f"cannot move directory: {old_relative}")
        git_mv(old_dir, new_dir)
        readme_relative = f"{old_relative}/README.md"
        if readme_relative in preludes:
            (new_dir / "README.md").write_text(preludes[readme_relative], encoding="utf-8")

    old_path_by_new: dict[Path, Path] = {new.resolve(): old.resolve() for old, new in file_map.items()}
    for old_relative, new_relative in DIR_MOVES.items():
        old_dir = (BOOK / old_relative).resolve()
        new_dir = (BOOK / new_relative).resolve()
        for path in new_dir.rglob("*.md"):
            old_path_by_new[path.resolve()] = old_dir / path.relative_to(new_dir)

    abs_dir_map = {
        old.resolve(): new.resolve()
        for old_relative, new_relative in DIR_MOVES.items()
        for old, new in [(BOOK / old_relative, BOOK / new_relative)]
    }
    abs_file_map = {old.resolve(): new.resolve() for old, new in file_map.items()}
    for path in sorted(BOOK.rglob("*.md")):
        old_source = old_path_by_new.get(path.resolve(), path.resolve())
        rewritten = rewrite_links(path.read_text(encoding="utf-8"), old_source, path.resolve(), abs_file_map, abs_dir_map)
        path.write_text(rewritten, encoding="utf-8")

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
        'summary: "按编号进入 Fifty 份完整技术记录与原始测量条件。"',
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
        metadata = baseline[source_id]
        source_index.append(
            f"| [{source_id}]({source_id}.md) | {source_titles[source_id]} | "
            f"{source_case.get(metadata['source'], '证据附录')} |"
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
        "实例页只保留适用范围、执行顺序、结果解释与证据入口；完整原始记录按编号存入证据卷。",
        "",
        "| 实例 | 平台 | 设备 | 来源 | 入口 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for case in CASES:
        ids = source_ids((sources_dir / "README.md").read_text(encoding="utf-8"))
        ids = sorted(
            source_id
            for source_id in baseline
            if baseline[source_id]["source"] == case.source
        )
        case_index.append(
            f"| {case.case_id} | {case.platform} | {case.device} | {', '.join(ids) or '无 R 原文'} | "
            f"[{case.target}]({case.target.removeprefix('cases/')}) |"
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
        "- [structured measurements](measurements.json)",
        "- [source coverage](source-coverage.json)",
        "",
        "证据卷不以摘要替代原始过程。实例页中的结论必须能回到 R/E 编号或结构化测量字段。",
        "",
    ]
    (BOOK / "evidence/README.md").write_text("\n".join(evidence_index), encoding="utf-8")
    (BOOK / "SUMMARY.md").write_text(
        build_summary(old_entries, abs_file_map, source_titles),
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
    sequence = 0
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
            chapter_id = f"T{sequence:02}"
            sequence += 1
        platform = next((case.platform for case in CASES if case.target == relative), infer_platform(relative, title))
        device = next((case.device for case in CASES if case.target == relative), "general")
        layer = next((case.layer for case in CASES if case.target == relative), infer_layer(relative, title))
        status = next((case.status for case in CASES if case.target == relative), infer_status(relative, title))
        sources = source_ids(text)
        path.write_text(
            front_matter(
                chapter_id,
                title,
                kind,
                volume,
                layer,
                platform,
                device,
                status,
                sources,
                first_paragraph(text),
            )
            + text.lstrip(),
            encoding="utf-8",
        )

    report = {
        "tutorial_documents": len(list(BOOK.rglob("*.md"))) - 14 - 50 - 4,
        "cases": len(CASES),
        "r_sources": len(seen_sources),
        "moved_originals": len(CASES) + len(EXTRA_MOVES),
        "evidence_hash_baseline": len(baseline),
    }
    (REPORTS / "migration-summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
