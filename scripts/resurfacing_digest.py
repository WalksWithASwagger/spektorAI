#!/usr/bin/env python3
"""Generate the local WhisperForge resurfacing digest."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from whisperforge_core import resurfacing  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument(
        "--include-all-captures",
        action="store_true",
        help="Include smoke/demo captures instead of default real-signal filtering.",
    )
    parser.add_argument("--route-to", choices=resurfacing.DIGEST_ROUTE_DESTINATIONS)
    parser.add_argument(
        "--approve-routing",
        action="store_true",
        help="Allow the selected digest routing destination to write.",
    )
    parser.add_argument(
        "--routing-dry-run",
        action="store_true",
        help="Preview approved routing without writing.",
    )
    parser.add_argument(
        "--followup-queue-path",
        default=os.getenv("WHISPERFORGE_HANDOFF_FOLLOWUP_QUEUE_PATH", ""),
        help="JSONL path for approved follow-up queue routing.",
    )
    parser.add_argument(
        "--notion-draft-dir",
        default=os.getenv("WHISPERFORGE_HANDOFF_NOTION_DRAFT_DIR", ""),
        help="Directory for approved Notion task/page draft files.",
    )
    args = parser.parse_args()
    digest = resurfacing.build_digest(
        limit=args.limit,
        include_nonprod=args.include_all_captures,
    )
    path = resurfacing.write_digest(
        args.output_dir,
        limit=args.limit,
        include_nonprod=args.include_all_captures,
        digest=digest,
    )
    print(path)
    if args.route_to:
        result = resurfacing.route_digest(
            digest,
            destination=args.route_to,
            approved=args.approve_routing,
            dry_run=args.routing_dry_run,
            queue_path=args.followup_queue_path,
            notion_draft_dir=args.notion_draft_dir,
        )
        print(_format_route_result(result))
    return 0


def _format_route_result(result) -> str:
    state = "dry-run" if result.dry_run else "created" if result.success else "failed"
    lines = [f"Routing {state}: {result.target}"]
    if result.url:
        lines.append(f"URL: {result.url}")
    if result.error:
        lines.append(f"Reason: {result.error}")
    if result.details.get("message"):
        lines.append(f"Note: {result.details['message']}")
    if result.details.get("draft_path"):
        lines.append(f"Draft path: {result.details['draft_path']}")
    if result.details.get("queue_path"):
        lines.append(f"Queue path: {result.details['queue_path']}")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
