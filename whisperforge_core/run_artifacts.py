"""Durable local artifacts for in-flight and completed runs."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .config import CACHE_DIR

RUNS_DIR = CACHE_DIR / "runs"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_run_id(now: Optional[datetime] = None) -> str:
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{uuid.uuid4().hex[:8]}"


def run_dir(run_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", run_id).strip(".-")
    if not safe:
        raise ValueError("run_id must contain at least one safe character")
    return RUNS_DIR / safe


def manifest_path(run_id: str) -> Path:
    return run_dir(run_id) / "manifest.json"


def load_manifest(run_id: str) -> dict:
    path = manifest_path(run_id)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def start_run(run_id: str, metadata: dict[str, Any]) -> Path:
    path = run_dir(run_id)
    path.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(run_id)
    manifest.update({
        "run_id": run_id,
        "status": "running",
        "created_at": manifest.get("created_at") or now_iso(),
        "updated_at": now_iso(),
        "metadata": metadata,
        "stages": manifest.get("stages", []),
        "exports": manifest.get("exports", []),
    })
    _write_json(manifest_path(run_id), manifest)
    return path


def write_stage(run_id: str, stage: str, payload: dict[str, Any]) -> Path:
    stage_path = run_dir(run_id) / "stages" / f"{_slug(stage)}.json"
    stage_record = {
        "run_id": run_id,
        "stage": stage,
        "updated_at": now_iso(),
        "payload": _jsonable(payload),
    }
    _write_json(stage_path, stage_record)

    manifest = load_manifest(run_id)
    stages = [
        item for item in manifest.get("stages", [])
        if item.get("stage") != stage
    ]
    stages.append({
        "stage": stage,
        "path": str(stage_path),
        "updated_at": stage_record["updated_at"],
    })
    manifest.update({
        "run_id": run_id,
        "status": manifest.get("status") or "running",
        "updated_at": stage_record["updated_at"],
        "current_stage": stage,
        "stages": stages,
    })
    _write_json(manifest_path(run_id), manifest)
    return stage_path


def record_export(run_id: str, kind: str, value: str) -> None:
    manifest = load_manifest(run_id)
    exports = [
        item for item in manifest.get("exports", [])
        if not (item.get("kind") == kind and item.get("value") == value)
    ]
    exports.append({"kind": kind, "value": value, "updated_at": now_iso()})
    manifest.update({
        "run_id": run_id,
        "updated_at": now_iso(),
        "exports": exports,
    })
    _write_json(manifest_path(run_id), manifest)


def mark_status(run_id: str, status: str, *, error: Optional[str] = None) -> None:
    manifest = load_manifest(run_id)
    manifest.update({
        "run_id": run_id,
        "status": status,
        "updated_at": now_iso(),
    })
    if error:
        manifest["error"] = error
    elif "error" in manifest:
        del manifest["error"]
    _write_json(manifest_path(run_id), manifest)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(
        json.dumps(_jsonable(data), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip(".-").lower()
    return slug or "stage"


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return str(value)
