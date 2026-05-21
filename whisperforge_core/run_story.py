"""Human-readable run timeline summaries."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class RunStoryStep:
    id: str
    label: str
    status: str
    detail: str
    timestamp: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def build_run_story(
    manifest: Mapping[str, Any],
    *,
    capture_metadata: Mapping[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Build a compact capture -> output -> export story from a run manifest."""
    metadata = _mapping(manifest.get("metadata"))
    capture = _mapping(capture_metadata) or _mapping(metadata.get("capture"))
    input_source = str(capture.get("source") or metadata.get("source") or "")
    settings = _mapping(metadata.get("settings"))
    recipe = _mapping(metadata.get("recipe"))
    stages = {
        str(item.get("stage") or "")
        for item in manifest.get("stages", [])
        if isinstance(item, Mapping)
    }
    exports = [
        dict(item)
        for item in manifest.get("exports", [])
        if isinstance(item, Mapping)
    ]
    status = str(manifest.get("status") or "unknown")
    failed = status == "failed"

    steps = [
        _capture_step(metadata, capture),
        _transcription_step(input_source, stages, failed),
        _context_step(settings, stages),
        _generation_step(status, stages, manifest),
        _review_step(stages, failed),
        _export_step(exports, failed),
    ]
    handoff = _handoff_step(recipe, exports)
    if handoff:
        steps.append(handoff)
    return [step.to_dict() for step in steps]


def _capture_step(metadata: Mapping[str, Any], capture: Mapping[str, Any]) -> RunStoryStep:
    source = str(capture.get("source") or metadata.get("source") or "unknown")
    title = str(capture.get("title") or metadata.get("filename") or "Input captured")
    status = str(capture.get("status") or "captured")
    detail = f"{_humanize(source)} input: {title}"
    if status and status not in {"captured", "completed"}:
        detail = f"{detail} ({status})"
    return RunStoryStep(
        id="capture",
        label="Capture",
        status="complete",
        detail=detail,
        timestamp=str(capture.get("updated_at") or _manifest_time(metadata)),
    )


def _transcription_step(
    source: str,
    stages: set[str],
    failed: bool,
) -> RunStoryStep:
    text_source = source in {"paste", "wispr_flow"}
    if "transcription" in stages:
        detail = (
            "Text input used; transcription was not needed."
            if text_source else "Audio transcription captured."
        )
        return RunStoryStep("transcription", "Transcription", "complete", detail)
    if failed:
        return RunStoryStep(
            "transcription",
            "Transcription",
            "error",
            "Run failed before transcription completed.",
        )
    return RunStoryStep("transcription", "Transcription", "waiting", "Waiting for transcript.")


def _context_step(settings: Mapping[str, Any], stages: set[str]) -> RunStoryStep:
    rag_mode = str(settings.get("rag_mode") or "auto")
    if "retrieval_inspector" in stages:
        return RunStoryStep(
            "context", "Knowledge context", "complete", "KB retrieval receipts were captured.",
        )
    if rag_mode == "never":
        return RunStoryStep(
            "context", "Knowledge context", "skipped", "RAG was disabled for this run.",
        )
    return RunStoryStep("context", "Knowledge context", "waiting", "No retrieval receipt recorded yet.")


def _generation_step(
    status: str,
    stages: set[str],
    manifest: Mapping[str, Any],
) -> RunStoryStep:
    if "session_output" in stages:
        return RunStoryStep(
            "generation",
            "Composition",
            "complete",
            "Draft outputs and stage artifacts are available.",
        )
    if status == "failed":
        error = str(manifest.get("error") or "Pipeline failed before outputs were completed.")
        return RunStoryStep("generation", "Composition", "error", error)
    if status == "running":
        current = str(manifest.get("current_stage") or "pipeline")
        return RunStoryStep("generation", "Composition", "active", f"Currently at {current}.")
    return RunStoryStep("generation", "Composition", "waiting", "No completed output artifact yet.")


def _review_step(stages: set[str], failed: bool) -> RunStoryStep:
    if "scorecard" in stages:
        return RunStoryStep("review", "Review", "complete", "Scorecard and review signals are ready.")
    if failed:
        return RunStoryStep("review", "Review", "waiting", "Review waits for a completed draft.")
    return RunStoryStep("review", "Review", "waiting", "No scorecard recorded yet.")


def _export_step(exports: list[dict[str, Any]], failed: bool) -> RunStoryStep:
    content_exports = [
        item for item in exports
        if str(item.get("kind") or "") in {"markdown", "notion", "vault"}
    ]
    if content_exports:
        kinds = ", ".join(_humanize(str(item.get("kind") or "")) for item in content_exports)
        return RunStoryStep("export", "Export", "complete", f"Recorded exports: {kinds}.")
    if failed:
        return RunStoryStep("export", "Export", "waiting", "Export waits for a completed run.")
    return RunStoryStep("export", "Export", "waiting", "No content export recorded yet.")


def _handoff_step(
    recipe: Mapping[str, Any],
    exports: list[dict[str, Any]],
) -> RunStoryStep | None:
    handoff_exports = [
        item for item in exports
        if str(item.get("kind") or "").startswith("handoff")
    ]
    if handoff_exports:
        kinds = ", ".join(_humanize(str(item.get("kind") or "")) for item in handoff_exports)
        return RunStoryStep("handoff", "Handoff", "complete", f"Recorded handoff artifact: {kinds}.")

    targets = _string_list(recipe.get("handoff_targets"))
    if not targets:
        effective = _mapping(recipe.get("effective_settings"))
        targets = _string_list(effective.get("handoff_targets"))
    if targets:
        return RunStoryStep(
            "handoff",
            "Handoff",
            "waiting",
            f"Configured targets: {', '.join(targets)}. Generate a draft when ready.",
        )
    return None


def _manifest_time(metadata: Mapping[str, Any]) -> str:
    return str(metadata.get("updated_at") or metadata.get("created_at") or "")


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return []


def _humanize(value: str) -> str:
    return value.replace("_", " ").strip().title() or "Unknown"
