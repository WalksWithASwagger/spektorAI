#!/usr/bin/env python3
"""Repository documentation reliability checks."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


PROJECT_DOCS = (
    "readme.md",
    "STATUS.md",
    "ROADMAP.md",
    "changelog.md",
)
DOC_GLOBS = (
    "docs/**/*.md",
    ".github/**/*.md",
)
FRESHNESS_FIELDS = {
    "STATUS.md": r"^Last updated: \d{4}-\d{2}-\d{2}$",
    "ROADMAP.md": r"^Last reviewed: \d{4}-\d{2}-\d{2}$",
    "docs/NEXT-ROUND-PLAN-2026-05-19.md": (
        r"^Last refreshed: \d{4}-\d{2}-\d{2}$"
    ),
    "docs/LINEAR-GITHUB-PIPELINE.md": r"^Last updated: \d{4}-\d{2}-\d{2}$",
    "docs/TRANSCRIPTION-PROVIDER-MATRIX-2026-05-18.md": (
        r"^_Last reviewed: \d{4}-\d{2}-\d{2}\. .+_$"
    ),
}


def collect_docs(root: Path) -> list[Path]:
    docs: set[Path] = set()
    for relative in PROJECT_DOCS:
        path = root / relative
        if path.exists():
            docs.add(path)
    for pattern in DOC_GLOBS:
        docs.update(path for path in root.glob(pattern) if path.is_file())
    return sorted(docs)


def make_targets(root: Path) -> set[str]:
    makefile = root / "Makefile"
    if not makefile.exists():
        return set()
    text = makefile.read_text(encoding="utf-8")
    return set(re.findall(r"^([A-Za-z0-9_.-]+):", text, flags=re.MULTILINE))


def check_links(root: Path, docs: list[Path]) -> list[str]:
    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    errors: list[str] = []
    for path in docs:
        for line_no, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        ):
            for match in link_pattern.finditer(line):
                link = match.group(1).strip()
                if not link or link.startswith(("#", "http://", "https://", "mailto:")):
                    continue
                link_path = link.split("#", 1)[0]
                target = (path.parent / link_path).resolve()
                if not target.exists():
                    rel = path.relative_to(root)
                    errors.append(f"{rel}:{line_no}: missing link target {link}")
    return errors


def check_make_refs(root: Path, docs: list[Path], targets: set[str]) -> list[str]:
    errors: list[str] = []
    for path in docs:
        in_fence = False
        for line_no, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        ):
            stripped = line.strip()
            if stripped.startswith("```"):
                in_fence = not in_fence
                continue

            refs = [
                match.group(1)
                for match in re.finditer(r"`make\s+([A-Za-z0-9_.-]+)`", line)
            ]
            if in_fence:
                command = re.match(r"^\s*make\s+([A-Za-z0-9_.-]+)\b", line)
                if command:
                    refs.append(command.group(1))

            for target in refs:
                if target not in targets:
                    rel = path.relative_to(root)
                    errors.append(f"{rel}:{line_no}: unknown Makefile target make {target}")
    return errors


def check_freshness(root: Path) -> list[str]:
    errors: list[str] = []
    for relative, pattern in FRESHNESS_FIELDS.items():
        path = root / relative
        if not path.exists():
            errors.append(f"{relative}: required freshness document is missing")
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        if not any(re.match(pattern, line) for line in lines[:8]):
            errors.append(f"{relative}: missing required freshness field matching {pattern}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="repository root to check")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    docs = collect_docs(root)
    targets = make_targets(root)

    errors = []
    errors.extend(check_links(root, docs))
    errors.extend(check_make_refs(root, docs, targets))
    errors.extend(check_freshness(root))

    if errors:
        print("docs-truth-check: failed")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"docs-truth-check: OK ({len(docs)} docs, {len(targets)} make targets)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
