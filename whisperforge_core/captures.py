"""Durable capture inbox records.

Captures are the source objects that feed runs: Wispr Flow paste, plain notes,
uploaded audio, or browser recordings. They live outside run artifacts because
one capture may be retried, re-run, or reused across multiple recipes.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .config import CACHE_DIR

CAPTURES_DIR = CACHE_DIR / "captures"
TEXT_IMPORT_SUFFIXES = {".txt", ".md", ".markdown"}
AUDIO_IMPORT_SUFFIXES = {".aac", ".aiff", ".flac", ".m4a", ".mp3", ".ogg", ".opus", ".wav", ".wma"}
TEMP_IMPORT_SUFFIXES = {".crdownload", ".part", ".temp", ".tmp"}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_capture_id(now: Optional[datetime] = None) -> str:
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    return f"cap-{stamp}-{uuid.uuid4().hex[:8]}"


def normalize_source(source: str) -> str:
    normalized = re.sub(r"[^a-z0-9_]+", "_", (source or "").lower()).strip("_")
    return normalized or "unknown"


@dataclass
class CaptureRecord:
    capture_id: str
    source: str
    title: str
    filename: str
    status: str = "captured"
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    input_path: Optional[str] = None
    text_excerpt: Optional[str] = None
    text_sha256: Optional[str] = None
    run_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CaptureRecord":
        return cls(
            capture_id=str(data.get("capture_id") or ""),
            source=normalize_source(str(data.get("source") or "unknown")),
            title=str(data.get("title") or "Untitled capture"),
            filename=str(data.get("filename") or ""),
            status=str(data.get("status") or "captured"),
            created_at=str(data.get("created_at") or now_iso()),
            updated_at=str(data.get("updated_at") or now_iso()),
            input_path=data.get("input_path"),
            text_excerpt=data.get("text_excerpt"),
            text_sha256=data.get("text_sha256"),
            run_ids=[str(v) for v in data.get("run_ids", [])],
            metadata=dict(data.get("metadata") or {}),
        )


def capture_dir(capture_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", capture_id).strip(".-")
    if not safe:
        raise ValueError("capture_id must contain at least one safe character")
    return CAPTURES_DIR / safe


def record_path(capture_id: str) -> Path:
    return capture_dir(capture_id) / "capture.json"


def create_capture(
    *,
    source: str,
    filename: str,
    title: Optional[str] = None,
    text: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    capture_id: Optional[str] = None,
) -> CaptureRecord:
    capture_id = capture_id or new_capture_id()
    source = normalize_source(source)
    path = capture_dir(capture_id)
    path.mkdir(parents=True, exist_ok=True)

    input_path: Optional[str] = None
    text_excerpt: Optional[str] = None
    text_sha256: Optional[str] = None
    if text is not None:
        input_file = path / "input.txt"
        input_file.write_text(text, encoding="utf-8")
        input_path = str(input_file)
        stripped = text.strip()
        text_excerpt = stripped[:320]
        text_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()

    record = CaptureRecord(
        capture_id=capture_id,
        source=source,
        title=title or _default_title(source, filename, text),
        filename=filename,
        input_path=input_path,
        text_excerpt=text_excerpt,
        text_sha256=text_sha256,
        metadata=metadata or {},
    )
    _write_record(record)
    return record


def import_capture_file(path: str | Path, *, source: str = "import_folder") -> CaptureRecord | None:
    file_path = Path(path)
    if not _is_import_candidate(file_path) or not file_path.is_file():
        return None

    source_path = _source_path(file_path)
    existing = _find_duplicate(source_path=source_path)
    if existing:
        return existing

    suffix = file_path.suffix.lower()
    metadata = {
        "source_path": source_path,
        "imported_from": str(file_path),
        "import_kind": "text" if suffix in TEXT_IMPORT_SUFFIXES else "audio",
    }
    if suffix in TEXT_IMPORT_SUFFIXES:
        text = file_path.read_text(encoding="utf-8")
        text_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
        existing = _find_duplicate(source_path=source_path, text_sha256=text_sha256)
        if existing:
            return existing
        return create_capture(
            source=source,
            filename=file_path.name,
            title=_default_title(source, file_path.name, text),
            text=text,
            metadata=metadata,
        )
    if suffix in AUDIO_IMPORT_SUFFIXES:
        return create_capture(
            source=source,
            filename=file_path.name,
            metadata=metadata,
        )
    return None


def import_capture_folder(path: str | Path, *, source: str = "import_folder") -> list[CaptureRecord]:
    folder = Path(path)
    if not folder.is_dir():
        raise ValueError(f"import folder does not exist: {folder}")

    records: list[CaptureRecord] = []
    for file_path in sorted(p for p in folder.rglob("*") if p.is_file()):
        record = import_capture_file(file_path, source=source)
        if record:
            records.append(record)
    return records


def load_capture(capture_id: str) -> CaptureRecord:
    data = json.loads(record_path(capture_id).read_text(encoding="utf-8"))
    return CaptureRecord.from_dict(data)


def list_captures(limit: int = 100) -> list[CaptureRecord]:
    if not CAPTURES_DIR.exists():
        return []
    records: list[tuple[float, CaptureRecord]] = []
    for path in CAPTURES_DIR.glob("*/capture.json"):
        try:
            records.append((
                path.stat().st_mtime,
                CaptureRecord.from_dict(json.loads(path.read_text(encoding="utf-8"))),
            ))
        except (OSError, json.JSONDecodeError):
            continue
    records.sort(key=lambda item: (item[0], item[1].updated_at), reverse=True)
    return [record for _mtime, record in records[:limit]]


def read_capture_text(capture_id: str) -> str:
    record = load_capture(capture_id)
    if not record.input_path:
        return ""
    path = Path(record.input_path)
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def attach_run(capture_id: str, run_id: str, *, status: str = "running") -> CaptureRecord:
    record = load_capture(capture_id)
    if run_id not in record.run_ids:
        record.run_ids.append(run_id)
    record.status = status
    record.updated_at = now_iso()
    _write_record(record)
    return record


def mark_status(capture_id: str, status: str) -> CaptureRecord:
    record = load_capture(capture_id)
    record.status = status
    record.updated_at = now_iso()
    _write_record(record)
    return record


def run_metadata(capture_id: Optional[str]) -> dict[str, Any] | None:
    if not capture_id:
        return None
    try:
        record = load_capture(capture_id)
    except (OSError, json.JSONDecodeError):
        return None
    return {
        "capture_id": record.capture_id,
        "source": record.source,
        "title": record.title,
        "filename": record.filename,
        "status": record.status,
        "input_path": record.input_path,
        "text_sha256": record.text_sha256,
        "text_excerpt": record.text_excerpt,
    }


def _write_record(record: CaptureRecord) -> None:
    path = record_path(record.capture_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(json.dumps(record.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _source_path(path: Path) -> str:
    return str(path.expanduser().resolve())


def _is_import_candidate(path: Path) -> bool:
    name = path.name
    if name.startswith(".") or name.startswith("chunk_") or "_chunk_" in name:
        return False
    suffix = path.suffix.lower()
    if suffix in TEMP_IMPORT_SUFFIXES or name.endswith("~"):
        return False
    return suffix in TEXT_IMPORT_SUFFIXES or suffix in AUDIO_IMPORT_SUFFIXES


def _find_duplicate(
    *,
    source_path: Optional[str] = None,
    text_sha256: Optional[str] = None,
) -> CaptureRecord | None:
    for record in list_captures(limit=10_000):
        if source_path and record.metadata.get("source_path") == source_path:
            return record
        if text_sha256 and record.text_sha256 == text_sha256:
            return record
    return None


def _default_title(source: str, filename: str, text: Optional[str]) -> str:
    if text and text.strip():
        first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
        if first_line:
            return first_line[:80]
    if filename:
        return Path(filename).stem.replace("-", " ").replace("_", " ").strip().title()
    return source.replace("_", " ").title() or "Untitled capture"
