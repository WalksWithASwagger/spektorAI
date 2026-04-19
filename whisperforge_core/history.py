"""Run history log.

Append-only JSONL record of every successful Notion export: which audio,
which provider/model, how long it ran, how much it cost, and a direct link
back to the Notion page. Read from the sidebar's "Recent runs" panel so
Kris can jump back into prior pieces without hunting through Notion.

Lives in ``CACHE_DIR/history.jsonl``.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from .config import CACHE_DIR
from .logging import get_logger

logger = get_logger(__name__)

HISTORY_FILE = CACHE_DIR / "history.jsonl"


@dataclass
class RunRecord:
    """One pipeline run, end-to-end."""
    timestamp: str                     # ISO-8601 UTC
    title: str                         # Notion page title
    notion_url: Optional[str] = None
    audio_filename: Optional[str] = None
    provider: str = ""
    model: str = ""
    duration_seconds: float = 0.0
    cost_usd: float = 0.0
    cache_savings_usd: float = 0.0
    flags: dict = field(default_factory=dict)   # {"agentic": bool, "fact_check": bool, "chapters": bool, "backend": str}

    def to_json_line(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"))


def _ensure_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def append(record: RunRecord) -> None:
    """Durable append of one run. Errors are logged but never raised —
    history is non-critical telemetry, not part of the success path."""
    try:
        _ensure_dir()
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(record.to_json_line() + "\n")
    except OSError as e:
        logger.warning("failed to append history record: %s", e)


def recent(limit: int = 10) -> List[RunRecord]:
    """Return the most recent ``limit`` records, newest first. Malformed
    lines are skipped silently rather than corrupting the whole view."""
    if not HISTORY_FILE.exists():
        return []
    try:
        lines = HISTORY_FILE.read_text(encoding="utf-8").splitlines()
    except OSError as e:
        logger.warning("failed to read history: %s", e)
        return []
    records: List[RunRecord] = []
    # Walk from the end so we honor ``limit`` without loading the whole file
    # into a list of RunRecords when it eventually gets long.
    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            records.append(RunRecord(**data))
        except (json.JSONDecodeError, TypeError) as e:
            logger.debug("skipping malformed history line: %s", e)
            continue
        if len(records) >= limit:
            break
    return records


def clear() -> int:
    """Remove the history file. Returns the number of records dropped."""
    if not HISTORY_FILE.exists():
        return 0
    try:
        count = sum(1 for _ in HISTORY_FILE.read_text().splitlines() if _.strip())
    except OSError:
        count = 0
    try:
        HISTORY_FILE.unlink()
    except OSError:
        pass
    return count
