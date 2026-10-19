"""Repair links outside the Chinese book after volume migration."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

from migrate_volumes import BOOK, CASES, EXTRA_MOVES


ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"(?<!!)\[([^]]+)]\((?P<target>[^)]+)\)")
OLD_PREFIX = "01-deployment-foundations/"


def path_map() -> dict[str, str]:
    mapping = {case.source: case.target for case in CASES}
    mapping.update(EXTRA_MOVES)
    mapping["engineering/README.md"] = "cases/README.md"
    return mapping


def migrate_target(raw: str, mapping: dict[str, str]) -> str | None:
    normalized = raw.lstrip("./")
    marker = f"{OLD_PREFIX}"
    index = normalized.find(marker)
    if index < 0:
        return None
    old_relative = normalized[index + len(marker) :]
    if old_relative.startswith("practice/first-service/"):
        return "cases/C14-windows-cpu/" + old_relative.removeprefix("practice/first-service/")
    if old_relative == "practice/first-service":
        return "cases/C14-windows-cpu/"
    return mapping.get(old_relative)


def main() -> None:
    mapping = path_map()
    changed = 0
    for path in sorted(ROOT.rglob("*.md")):
        relative = path.relative_to(ROOT).as_posix()
        if relative.startswith("docs/01-deployment-foundations/") or relative.startswith("reports/"):
            continue
        text = path.read_text(encoding="utf-8")

        def replace(match: re.Match[str]) -> str:
            nonlocal changed
            label, target = match.groups()
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                return match.group(0)
            resolved = (path.parent / unquote(parsed.path)).resolve()
            if resolved.exists():
                return match.group(0)
            new_relative = migrate_target(unquote(parsed.path), mapping)
            if not new_relative:
                return match.group(0)
            new_target = BOOK / new_relative
            if not new_target.exists():
                return match.group(0)
            import os

            updated = os.path.relpath(new_target, path.parent).replace(os.sep, "/")
            if parsed.fragment:
                updated += "#" + parsed.fragment
            changed += 1
            return f"[{label}]({updated})"

        updated_text = LINK.sub(replace, text)
        if updated_text != text:
            path.write_text(updated_text, encoding="utf-8")
    print(f"Updated {changed} links.")


if __name__ == "__main__":
    main()
