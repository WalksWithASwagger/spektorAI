#!/usr/bin/env python3
"""Review an agent-created PR against issue acceptance criteria."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from common import read_text_arg, write_json  # noqa: E402


def normalize_checkbox_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).lower()


def extract_checkboxes(markdown: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for match in re.finditer(r"^-\s+\[([ xX])\]\s+(.+)$", markdown, flags=re.MULTILINE):
        raw = match.group(2).strip()
        items.append(
            {
                "checked": match.group(1).lower() == "x",
                "text": raw,
                "normalized": normalize_checkbox_text(raw),
            }
        )
    return items


def section_body(markdown: str, title: str) -> str:
    pattern = rf"^##\s+{re.escape(title)}\s*$"
    match = re.search(pattern, markdown, flags=re.IGNORECASE | re.MULTILINE)
    if not match:
        return ""
    remaining = markdown[match.end():]
    next_heading = re.search(r"^##\s+", remaining, flags=re.MULTILINE)
    if not next_heading:
        return remaining
    return remaining[: next_heading.start()]


def linked_issue_number(pr_body: str) -> str | None:
    match = re.search(r"\bCloses\s+#(\d+)", pr_body, flags=re.IGNORECASE)
    return match.group(1) if match else None


def acceptance_coverage(
    issue_acceptance: list[dict[str, Any]],
    pr_self_check: list[dict[str, Any]],
) -> tuple[bool, list[str], list[str]]:
    pr_checked = {
        item["normalized"] for item in pr_self_check if item["checked"]
    }
    missing = [
        item["text"]
        for item in issue_acceptance
        if item["normalized"] not in pr_checked
    ]
    unchecked = [
        item["text"]
        for item in pr_self_check
        if not item["checked"]
    ]
    return (len(missing) == 0 and len(unchecked) == 0), missing, unchecked


def review_pr(
    issue_body: str, pr_body: str, additions: int, deletions: int, changed_files: int
) -> dict[str, Any]:
    issue_section = section_body(issue_body, "Acceptance Criteria") or issue_body
    pr_section = section_body(pr_body, "Acceptance Self-Check")
    issue_checks = extract_checkboxes(issue_section)
    pr_checks = extract_checkboxes(pr_section)
    has_link = linked_issue_number(pr_body) is not None
    has_verification = bool(
        re.search(r"^##\s+Verification\s*$", pr_body, re.IGNORECASE | re.MULTILINE)
    )
    has_self_check = bool(
        re.search(r"^##\s+Acceptance Self-Check\s*$", pr_body, re.IGNORECASE | re.MULTILINE)
    )
    coverage_ok, missing_acceptance, unchecked_self_checks = acceptance_coverage(
        issue_checks, pr_checks
    )
    changed_lines = additions + deletions
    within_limits = changed_files <= 20 and changed_lines <= 500
    ok = (
        bool(issue_checks)
        and has_link
        and has_verification
        and has_self_check
        and coverage_ok
        and within_limits
    )
    return {
        "ok": ok,
        "verdict": "review-ready" if ok else "needs-human",
        "linked_issue": linked_issue_number(pr_body),
        "issue_acceptance_count": len(issue_checks),
        "pr_self_check_count": len(pr_checks),
        "acceptance_coverage_ok": coverage_ok,
        "missing_acceptance_items": missing_acceptance,
        "unchecked_self_checks": unchecked_self_checks,
        "has_verification": has_verification,
        "has_self_check": has_self_check,
        "within_limits": within_limits,
        "changed_files": changed_files,
        "changed_lines": changed_lines,
        "comment": build_comment(
            ok,
            issue_checks,
            missing_acceptance,
            unchecked_self_checks,
            has_link,
            has_verification,
            has_self_check,
            coverage_ok,
            within_limits,
        ),
    }


def build_comment(
    ok: bool,
    issue_checks: list[dict[str, Any]],
    missing_acceptance: list[str],
    unchecked_self_checks: list[str],
    has_link: bool,
    has_verification: bool,
    has_self_check: bool,
    coverage_ok: bool,
    within_limits: bool,
) -> str:
    lines = [
        "## Agentic PR Review",
        "",
        f"Verdict: {'review-ready' if ok else 'needs-human'}",
        "",
        "Checks:",
        f"- Linked issue via `Closes #...`: {'yes' if has_link else 'no'}",
        f"- Issue acceptance criteria found: {len(issue_checks)}",
        f"- PR verification section present: {'yes' if has_verification else 'no'}",
        f"- PR acceptance self-check present: {'yes' if has_self_check else 'no'}",
        f"- PR self-check covers issue acceptance: {'yes' if coverage_ok else 'no'}",
        f"- Diff within v1 limits: {'yes' if within_limits else 'no'}",
    ]
    if missing_acceptance:
        lines.append("- Missing acceptance coverage:")
        lines.extend(f"  - {item}" for item in missing_acceptance)
    if unchecked_self_checks:
        lines.append("- Unchecked PR self-check items:")
        lines.extend(f"  - {item}" for item in unchecked_self_checks)
    if not ok:
        lines.extend(
            [
                "",
                "This PR is not blocked from human review, but the agentic gate is not satisfied.",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue-file", required=True)
    parser.add_argument("--pr-body-file", required=True)
    parser.add_argument("--additions", type=int, default=0)
    parser.add_argument("--deletions", type=int, default=0)
    parser.add_argument("--changed-files", type=int, default=0)
    parser.add_argument("--json-output", required=True)
    args = parser.parse_args()
    result = review_pr(
        read_text_arg(args.issue_file),
        read_text_arg(args.pr_body_file),
        args.additions,
        args.deletions,
        args.changed_files,
    )
    write_json(Path(args.json_output), result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
