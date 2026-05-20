#!/usr/bin/env python3
"""Generate the local WhisperForge resurfacing digest."""

from __future__ import annotations

import argparse
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
    args = parser.parse_args()
    path = resurfacing.write_digest(
        args.output_dir,
        limit=args.limit,
        include_nonprod=args.include_all_captures,
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
