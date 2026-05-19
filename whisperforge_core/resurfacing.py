"""Report-only resurfacing digest for captures and run artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
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
    "Weekly recaps",
    "Topic evolution",
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

    for recap in build_weekly_recaps(capture_records, manifests):
        sections["Weekly recaps"].append(DigestEntry(
            recap["title"], "weekly-recap", recap["detail"],
        ))
    for topic in build_topic_evolution(capture_records, manifests):
        sections["Topic evolution"].append(DigestEntry(
            topic["title"], "topic-evolution", topic["detail"],
        ))

    return {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "report-only",
        "sections": {
            name: [entry.__dict__ for entry in entries]
            for name, entries in sections.items()
        },
    }


def build_weekly_recaps(
    capture_records: list[captures.CaptureRecord],
    manifests: list[dict[str, Any]],
) -> list[dict[str, str]]:
    weeks: dict[str, dict[str, Any]] = {}
    for record in capture_records:
        week = _week_label(record.created_at or record.updated_at)
        bucket = weeks.setdefault(week, {"captures": [], "runs": []})
        bucket["captures"].append(record)
    for manifest in manifests:
        week = _week_label(str(manifest.get("created_at") or manifest.get("updated_at") or ""))
        bucket = weeks.setdefault(week, {"captures": [], "runs": []})
        bucket["runs"].append(manifest)

    recaps: list[dict[str, str]] = []
    for week in sorted(weeks, reverse=True):
        bucket = weeks[week]
        capture_count = len(bucket["captures"])
        run_count = len(bucket["runs"])
        completed = sum(1 for item in bucket["runs"] if item.get("status") == "completed")
        unresolved = sum(1 for item in bucket["captures"] if item.status not in {"completed", "archived"})
        unresolved += sum(1 for item in bucket["runs"] if item.get("status") != "completed" or item.get("error"))
        topics = _top_topics(bucket["captures"], bucket["runs"])
        topic_detail = f" Top topics: {', '.join(topics)}." if topics else ""
        recaps.append({
            "title": week,
            "detail": (
                f"{capture_count} captures, {run_count} runs, {completed} completed runs, "
                f"{unresolved} unresolved items.{topic_detail}"
            ),
        })
    return recaps


def build_topic_evolution(
    capture_records: list[captures.CaptureRecord],
    manifests: list[dict[str, Any]],
) -> list[dict[str, str]]:
    weekly_topics: dict[str, dict[str, int]] = {}
    for record in capture_records:
        week = _week_label(record.created_at or record.updated_at)
        for topic in _capture_topics(record):
            weekly_topics.setdefault(week, {})
            weekly_topics[week][topic] = weekly_topics[week].get(topic, 0) + 1
    for manifest in manifests:
        week = _week_label(str(manifest.get("created_at") or manifest.get("updated_at") or ""))
        for topic in _manifest_topics(manifest):
            weekly_topics.setdefault(week, {})
            weekly_topics[week][topic] = weekly_topics[week].get(topic, 0) + 1

    topic_weeks: dict[str, list[tuple[str, int]]] = {}
    for week, counts in weekly_topics.items():
        for topic, count in counts.items():
            topic_weeks.setdefault(topic, []).append((week, count))

    ranked_summaries: list[tuple[int, str, dict[str, str]]] = []
    for topic in sorted(topic_weeks):
        history = sorted(topic_weeks[topic])
        first_week = history[0][0]
        latest_week, latest_count = history[-1]
        total = sum(count for _week, count in history)
        span = len(history)
        week_word = "week" if span == 1 else "weeks"
        summary = {
            "title": topic,
            "detail": (
                f"First seen {first_week}; latest {latest_week} with {latest_count} signals; "
                f"{total} total signals across {span} {week_word}."
            ),
        }
        ranked_summaries.append((total, topic, summary))
    ranked_summaries.sort(key=lambda item: (-item[0], item[1]))
    return [summary for _total, _topic, summary in ranked_summaries]


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


def _top_topics(
    capture_records: list[captures.CaptureRecord],
    manifests: list[dict[str, Any]],
) -> list[str]:
    counts: dict[str, int] = {}
    for record in capture_records:
        for topic in _capture_topics(record):
            counts[topic] = counts.get(topic, 0) + 1
    for manifest in manifests:
        for topic in _manifest_topics(manifest):
            counts[topic] = counts.get(topic, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [topic for topic, _count in ranked[:3]]


def _capture_topics(record: captures.CaptureRecord) -> list[str]:
    metadata = record.metadata or {}
    topics = _metadata_topics(metadata)
    if not topics and record.source:
        topics.append(record.source)
    return topics


def _manifest_topics(manifest: dict[str, Any]) -> list[str]:
    metadata = manifest.get("metadata") or {}
    topics = _metadata_topics(metadata)
    recipe = metadata.get("recipe")
    if isinstance(recipe, dict):
        recipe_name = recipe.get("name") or recipe.get("recipe_name") or recipe.get("id") or recipe.get("recipe_id")
        if recipe_name:
            topics.append(str(recipe_name))
    elif recipe:
        topics.append(str(recipe))
    source = metadata.get("source")
    if source:
        topics.append(str(source))
    return _dedupe_topics(topics)


def _metadata_topics(metadata: dict[str, Any]) -> list[str]:
    topics: list[str] = []
    for key in ("topics", "topic", "tags", "tag", "keywords", "keyword"):
        topics.extend(_as_topic_list(metadata.get(key)))
    return _dedupe_topics(topics)


def _as_topic_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(part).strip() for part in value if str(part).strip()]
    return [str(value).strip()]


def _dedupe_topics(topics: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for topic in topics:
        label = " ".join(str(topic).strip().lower().split())
        if not label or label in seen:
            continue
        seen.add(label)
        normalized.append(label)
    return normalized


def _week_label(value: str) -> str:
    parsed = _parse_datetime(value)
    year, week, _weekday = parsed.isocalendar()
    return f"{year}-W{week:02d}"


def _parse_datetime(value: str) -> datetime:
    if value:
        candidate = value.strip()
        if candidate.endswith("Z"):
            candidate = f"{candidate[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            pass
    return datetime.fromtimestamp(0, tz=timezone.utc)
