"""Report-only resurfacing digest for captures and run artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from . import captures, run_artifacts
from .config import CACHE_DIR

DIGEST_SECTIONS = [
    "Notable captures",
    "Unresolved follow-ups",
    "Strong outputs",
    "Stale drafts",
    "Reusable source nuggets",
]
DEFAULT_DIGEST_DIR = CACHE_DIR / "digests"


@dataclass
class DigestEntry:
    title: str
    source: str
    detail: str
    link: str = ""


def build_digest(limit: int = 50, *, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now()
    capture_records = captures.list_captures(limit=limit)
    manifests = run_artifacts.list_manifests(limit=limit)
    sections = {name: [] for name in DIGEST_SECTIONS}

    for record in capture_records:
        link = record.input_path or str(captures.record_path(record.capture_id))
        if record.text_excerpt:
            sections["Notable captures"].append(DigestEntry(
                record.title, f"capture:{record.capture_id}", record.text_excerpt, link,
            ))
            sections["Reusable source nuggets"].append(DigestEntry(
                record.title, f"capture:{record.capture_id}", record.text_excerpt[:180], link,
            ))
        if record.status not in {"completed", "archived"}:
            sections["Unresolved follow-ups"].append(DigestEntry(
                record.title, f"capture:{record.capture_id}", f"Capture status is `{record.status}`.", link,
            ))

    for manifest in manifests:
        summary = run_artifacts.summarize_manifest(manifest)
        run_id = summary["run_id"]
        link = manifest.get("_path", "")
        output = run_artifacts.load_stage_payload(run_id, "session_output") if run_id else {}
        scorecard = run_artifacts.load_stage_payload(run_id, "scorecard") if run_id else {}
        score = scorecard.get("average_score") if isinstance(scorecard, dict) else None
        title = _run_title(output, run_id)
        if summary["partial"] or summary["error"]:
            sections["Unresolved follow-ups"].append(DigestEntry(
                title, f"run:{run_id}", summary["error"] or f"Partial at `{summary['current_stage'] or 'unknown'}`.", link,
            ))
        if isinstance(score, (int, float)) and score >= 80:
            sections["Strong outputs"].append(DigestEntry(
                title, f"run:{run_id}", f"Scorecard `{scorecard.get('verdict_label', 'Ready')}` at {int(score)}/100.", link,
            ))
        if summary["status"] == "completed" and summary["exports"] == "none":
            sections["Stale drafts"].append(DigestEntry(
                title, f"run:{run_id}", "Completed run has no recorded exports.", link,
            ))
        if output.get("wisdom"):
            sections["Reusable source nuggets"].append(DigestEntry(
                title, f"run:{run_id}", str(output["wisdom"])[:240], link,
            ))

    return {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "report-only",
        "sections": {
            name: [entry.__dict__ for entry in entries]
            for name, entries in sections.items()
        },
    }


def render_markdown(digest: dict[str, Any]) -> str:
    parts = [
        "# WhisperForge Resurfacing Digest",
        "",
        f"Generated: {digest.get('generated_at', '')}",
        "Mode: report-only. Do not route, publish, or notify without explicit confirmation.",
        "",
    ]
    sections = digest.get("sections") or {}
    for section in DIGEST_SECTIONS:
        entries = sections.get(section) or []
        parts.append(f"## {section}")
        if not entries:
            parts.append("- No signal found.")
        for entry in entries:
            link = f" ({entry.get('link')})" if entry.get("link") else ""
            parts.append(f"- **{entry.get('title', 'Untitled')}** [{entry.get('source', 'source')}]{link}: {entry.get('detail', '')}")
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def write_digest(out_dir: Path | None = None, *, limit: int = 50) -> Path:
    out_dir = out_dir or DEFAULT_DIGEST_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    digest = build_digest(limit=limit)
    stamp = digest["generated_at"][:10]
    path = out_dir / f"{stamp}-resurfacing-digest.md"
    path.write_text(render_markdown(digest), encoding="utf-8")
    return path


def _run_title(output: dict[str, Any], run_id: str) -> str:
    article = str(output.get("article") or "").strip()
    if article:
        first = next((line.strip("# ").strip() for line in article.splitlines() if line.strip()), "")
        if first:
            return first[:80]
    return run_id or "Run artifact"
