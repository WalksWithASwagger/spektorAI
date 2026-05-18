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
    args = parser.parse_args()
    path = resurfacing.write_digest(args.output_dir, limit=args.limit)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
