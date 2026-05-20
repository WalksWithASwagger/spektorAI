"""Durable local artifacts for in-flight and completed runs."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .config import CACHE_DIR

RUNS_DIR = CACHE_DIR / "runs"
ARTIFACT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ManifestStage:
    stage: str
    path: str
    updated_at: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ManifestStage":
        return cls(
            stage=str(data.get("stage") or ""),
            path=str(data.get("path") or ""),
            updated_at=str(data.get("updated_at") or ""),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "stage": self.stage,
            "path": self.path,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class ManifestExport:
    kind: str
    value: str
    updated_at: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ManifestExport":
        return cls(
            kind=str(data.get("kind") or ""),
            value=str(data.get("value") or ""),
            updated_at=str(data.get("updated_at") or ""),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "kind": self.kind,
            "value": self.value,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class RunManifest:
    run_id: str
    status: str = "running"
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    stages: list[ManifestStage] = field(default_factory=list)
    exports: list[ManifestExport] = field(default_factory=list)
    current_stage: str = ""
    error: str = ""
    artifact_schema_version: int = ARTIFACT_SCHEMA_VERSION

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunManifest":
        stages = [
            ManifestStage.from_dict(item)
            for item in data.get("stages", [])
            if isinstance(item, dict)
        ]
        exports = [
            ManifestExport.from_dict(item)
            for item in data.get("exports", [])
            if isinstance(item, dict)
        ]
        metadata = data.get("metadata")
        return cls(
            run_id=str(data.get("run_id") or ""),
            status=str(data.get("status") or "running"),
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
            metadata=metadata if isinstance(metadata, dict) else {},
            stages=stages,
            exports=exports,
            current_stage=str(data.get("current_stage") or ""),
            error=str(data.get("error") or ""),
            artifact_schema_version=_schema_version(data.get("artifact_schema_version")),
        )

    def to_dict(self) -> dict[str, Any]:
        data = {
            "artifact_schema_version": self.artifact_schema_version,
            "run_id": self.run_id,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": _jsonable(self.metadata),
            "stages": [stage.to_dict() for stage in self.stages],
            "exports": [item.to_dict() for item in self.exports],
        }
        if self.current_stage:
            data["current_stage"] = self.current_stage
        if self.error:
            data["error"] = self.error
        return data


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
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {}
    return RunManifest.from_dict(raw).to_dict()


def list_manifests(limit: int = 50) -> list[dict[str, Any]]:
    if not RUNS_DIR.exists():
        return []
    manifests = []
    for path in RUNS_DIR.glob("*/manifest.json"):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                continue
            manifest = RunManifest.from_dict(raw).to_dict()
            manifest["_path"] = str(path)
            manifests.append(manifest)
        except (OSError, json.JSONDecodeError):
            continue
    manifests.sort(
        key=lambda item: item.get("updated_at") or item.get("created_at") or "",
        reverse=True,
    )
    return manifests[:limit]


def summarize_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    metadata = manifest.get("metadata") or {}
    recipe = metadata.get("recipe") or {}
    settings = metadata.get("settings") or {}
    stages = manifest.get("stages") or []
    stage_names = {item.get("stage") for item in stages if isinstance(item, dict)}
    return {
        "run_id": manifest.get("run_id") or "",
        "status": manifest.get("status") or "unknown",
        "created_at": manifest.get("created_at") or "",
        "updated_at": manifest.get("updated_at") or "",
        "input_type": metadata.get("source") or "",
        "current_stage": manifest.get("current_stage") or "",
        "recipe": (
            recipe.get("name")
            or recipe.get("recipe_name")
            or recipe.get("id")
            or recipe.get("recipe_id")
            or "manual"
        ),
        "settings": ", ".join(k for k, v in settings.items() if v) or "none",
        "exports": ", ".join(item.get("kind", "") for item in manifest.get("exports", [])) or "none",
        "error": manifest.get("error") or "",
        "partial": manifest.get("status") != "completed" or "session_output" not in stage_names,
    }


def load_stage_payload(run_id: str, stage: str) -> dict[str, Any]:
    manifest = load_manifest(run_id)
    for item in manifest.get("stages", []):
        if item.get("stage") != stage:
            continue
        path = Path(item.get("path", ""))
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        payload = data.get("payload")
        return payload if isinstance(payload, dict) else {}
    return {}


def start_run(run_id: str, metadata: dict[str, Any]) -> Path:
    path = run_dir(run_id)
    path.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(run_id)
    manifest.update({
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
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
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
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


def refresh_capture_metadata(run_id: str, capture_metadata: dict[str, Any] | None) -> None:
    if not capture_metadata:
        return
    manifest = load_manifest(run_id)
    metadata = manifest.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    metadata["capture"] = _jsonable(capture_metadata)
    manifest.update({
        "run_id": run_id,
        "metadata": metadata,
        "updated_at": now_iso(),
    })
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


def _schema_version(value: Any) -> int:
    try:
        return int(value or ARTIFACT_SCHEMA_VERSION)
    except (TypeError, ValueError):
        return ARTIFACT_SCHEMA_VERSION


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
