"""Deterministic advisory scorecards for generated outputs."""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping


_STOPWORDS = {
    "about", "after", "again", "also", "because", "been", "being", "from",
    "have", "into", "just", "more", "most", "that", "their", "there",
    "these", "this", "through", "with", "when", "where", "which", "while",
    "will", "your",
}

_OUTPUT_ALIASES = {
    "transcript": "transcript",
    "wisdom": "wisdom",
    "outline": "outline",
    "social": "social_content",
    "social_content": "social_content",
    "image_prompts": "image_prompts",
    "article": "article",
    "source_receipts": "source_receipts",
    "chapters": "chapters",
}


def build_summary(
    *,
    article: str = "",
    transcript: str = "",
    wisdom: str = "",
    outline: str = "",
    social_content: str = "",
    image_prompts: str = "",
    chapters: Iterable[Mapping[str, Any]] | None = None,
    source_receipts: Iterable[Mapping[str, Any]] | None = None,
    retrieval_inspector: Mapping[str, Any] | None = None,
    fact_check_flags: Iterable[Mapping[str, Any]] | None = None,
    fact_check_ran: bool = False,
    recipe: Mapping[str, Any] | None = None,
    recipe_effective_settings: Mapping[str, Any] | None = None,
    exports: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    receipts = [dict(item) for item in source_receipts or [] if isinstance(item, Mapping)]
    flags = [dict(item) for item in fact_check_flags or [] if isinstance(item, Mapping)]
    recipe_meta = recipe_effective_settings or recipe or {}
    output_state = {
        "transcript": bool(transcript.strip()),
        "wisdom": bool(wisdom.strip()),
        "outline": bool(outline.strip()),
        "social_content": bool(social_content.strip()),
        "image_prompts": bool(image_prompts.strip()),
        "article": bool(article.strip()),
        "source_receipts": bool(receipts),
        "chapters": bool(list(chapters or [])),
    }
    retrieval = _retrieval_counts(retrieval_inspector)

    dimensions = [
        _voice_dimension(article, retrieval, recipe_meta),
        _grounding_dimension(article, transcript, receipts, retrieval, flags, fact_check_ran),
        _usefulness_dimension(article, output_state),
        _recipe_dimension(recipe_meta, output_state, flags, fact_check_ran),
        _handoff_dimension(article, receipts, flags, recipe_meta, list(exports or [])),
    ]
    average = round(sum(item["score"] for item in dimensions) / len(dimensions))
    verdict = _verdict(average, dimensions)
    return {
        "advisory": True,
        "blocks_save": False,
        "average_score": average,
        "verdict": verdict,
        "verdict_label": verdict.replace("_", " ").title(),
        "dimensions": dimensions,
    }


def compact_verdict(summary: Mapping[str, Any] | None) -> str:
    if not isinstance(summary, Mapping):
        return "Scorecard unavailable"
    label = str(summary.get("verdict_label") or "Review")
    score = summary.get("average_score")
    if isinstance(score, (int, float)):
        return f"{label} · {int(score)}/100"
    return label


def receipt_for_summary(summary: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source": "Scorecard",
        "verdict": compact_verdict(summary),
        "advisory": "yes" if summary.get("advisory", True) else "no",
        "blocks_save": "yes" if summary.get("blocks_save") else "no",
    }


def _voice_dimension(
    article: str,
    retrieval: Mapping[str, Any],
    recipe_meta: Mapping[str, Any],
) -> dict[str, Any]:
    notes = []
    score = 0
    if article.strip():
        score += 35
        notes.append("Draft is present.")
    if _word_count(article) >= 250:
        score += 15
        notes.append("Draft has enough length to judge voice.")
    anchors = retrieval.get("voice_anchors") or []
    if anchors:
        score += 30
        notes.append(f"KB voice anchors used: {', '.join(anchors[:3])}.")
    else:
        notes.append("No KB voice anchors detected; review voice manually.")
    if recipe_meta.get("recipe_id") or recipe_meta.get("name") or recipe_meta.get("recipe_name"):
        score += 10
        notes.append("Recipe context is attached.")
    if _has_voice_markers(article):
        score += 10
        notes.append("Draft includes first-person/editorial voice markers.")
    return _dimension("voice", "Voice", score, notes)


def _grounding_dimension(
    article: str,
    transcript: str,
    receipts: list[dict[str, Any]],
    retrieval: Mapping[str, Any],
    flags: list[dict[str, Any]],
    fact_check_ran: bool,
) -> dict[str, Any]:
    notes = []
    score = 0
    if article.strip() and transcript.strip():
        score += 25
        notes.append("Draft and transcript are both present.")
    if receipts:
        score += 20
        notes.append(f"{len(receipts)} source receipt(s) attached.")
    overlap = _overlap_ratio(article, transcript)
    if overlap >= 0.18:
        score += 25
        notes.append("Draft vocabulary strongly overlaps the source.")
    elif overlap >= 0.08:
        score += 12
        notes.append("Draft has partial source overlap.")
    else:
        notes.append("Low transcript overlap; inspect source support.")
    if retrieval.get("hits", 0):
        score += 10
        notes.append(f"{retrieval['hits']} retrieval hit(s) available.")
    if fact_check_ran and not flags:
        score += 20
        notes.append("Fact-check ran with no flags.")
    elif flags:
        score -= min(40, len(flags) * 20)
        notes.append(f"{len(flags)} fact-check flag(s) need review.")
    else:
        notes.append("Fact-check was not run.")
    return _dimension("grounding", "Grounding", score, notes)


def _usefulness_dimension(article: str, output_state: Mapping[str, bool]) -> dict[str, Any]:
    useful_outputs = [
        name for name in ("article", "wisdom", "outline", "social_content", "image_prompts")
        if output_state.get(name)
    ]
    score = 20 + (len(useful_outputs) * 14)
    notes = [f"Generated outputs: {', '.join(useful_outputs) or 'none'}."]
    words = _word_count(article)
    if words >= 500:
        score += 10
        notes.append("Article is long enough for publish/review use.")
    elif words:
        score += 5
        notes.append("Article is brief; useful for handoff or expansion.")
    if output_state.get("chapters"):
        score += 5
        notes.append("Chapters add navigation.")
    return _dimension("usefulness", "Usefulness", score, notes)


def _recipe_dimension(
    recipe_meta: Mapping[str, Any],
    output_state: Mapping[str, bool],
    flags: list[dict[str, Any]],
    fact_check_ran: bool,
) -> dict[str, Any]:
    expected = _string_list(recipe_meta.get("output_sections"))
    checks = _string_list(recipe_meta.get("eval_checks"))
    if not expected and not checks:
        return _dimension(
            "recipe_compliance",
            "Recipe Compliance",
            100,
            ["Manual run; no recipe requirements configured."],
        )

    missing = [
        section for section in expected
        if not output_state.get(_OUTPUT_ALIASES.get(section, section), False)
    ]
    missing_checks = []
    if "source_receipts" in checks and not output_state.get("source_receipts"):
        missing_checks.append("source_receipts")
    if "fact_check_flags" in checks:
        if not fact_check_ran:
            missing_checks.append("fact_check_not_run")
        elif flags:
            missing_checks.append("fact_check_flags_review")

    total = max(1, len(expected) + len(checks))
    misses = len(missing) + len(missing_checks)
    score = round(100 * max(0, total - misses) / total)
    notes = []
    if missing:
        notes.append(f"Missing recipe outputs: {', '.join(missing)}.")
    else:
        notes.append("Requested recipe outputs are present.")
    if missing_checks:
        notes.append(f"Eval checks need review: {', '.join(missing_checks)}.")
    elif checks:
        notes.append("Recipe eval checks look satisfied.")
    return _dimension("recipe_compliance", "Recipe Compliance", score, notes)


def _handoff_dimension(
    article: str,
    receipts: list[dict[str, Any]],
    flags: list[dict[str, Any]],
    recipe_meta: Mapping[str, Any],
    exports: list[Mapping[str, Any]],
) -> dict[str, Any]:
    targets = _string_list(recipe_meta.get("handoff_targets"))
    exported_kinds = {
        str(item.get("kind"))
        for item in exports
        if isinstance(item, Mapping) and item.get("kind")
    }
    score = 0
    notes = []
    if article.strip():
        score += 30
        notes.append("Draft is ready for handoff review.")
    if receipts:
        score += 25
        notes.append("Source receipts travel with the handoff.")
    if not flags:
        score += 15
        notes.append("No fact-check flags are currently open.")
    else:
        notes.append("Open fact-check flags should be resolved before publishing.")
    if targets:
        score += 15
        notes.append(f"Handoff targets: {', '.join(targets)}.")
    else:
        score += 5
        notes.append("No explicit handoff targets configured.")
    if exported_kinds:
        score += 15
        notes.append(f"Recorded exports: {', '.join(sorted(exported_kinds))}.")
    else:
        notes.append("No export has been recorded yet.")
    return _dimension("handoff_readiness", "Handoff Readiness", score, notes)


def _dimension(id_: str, label: str, score: int | float, notes: list[str]) -> dict[str, Any]:
    bounded = max(0, min(100, int(round(score))))
    if bounded >= 80:
        status = "strong"
    elif bounded >= 60:
        status = "review"
    else:
        status = "attention"
    return {
        "id": id_,
        "label": label,
        "score": bounded,
        "status": status,
        "notes": notes,
    }


def _verdict(average: int, dimensions: list[dict[str, Any]]) -> str:
    low = min(item["score"] for item in dimensions)
    if low < 50:
        return "needs_review"
    if average >= 80 and low >= 65:
        return "ready"
    return "review"


def _retrieval_counts(inspector: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(inspector, Mapping):
        return {"hits": 0, "voice_anchors": []}
    stages = inspector.get("stages") or {}
    hits = [
        hit
        for stage_hits in (stages.values() if isinstance(stages, Mapping) else [])
        for hit in (stage_hits or [])
        if isinstance(hit, Mapping)
    ]
    anchors = sorted({
        str(hit.get("doc_name"))
        for hit in hits
        if hit.get("role") == "voice_anchor" and hit.get("doc_name")
    })
    return {"hits": len(hits), "voice_anchors": anchors}


def _overlap_ratio(article: str, transcript: str) -> float:
    article_tokens = _tokens(article)
    transcript_tokens = _tokens(transcript)
    if not article_tokens or not transcript_tokens:
        return 0.0
    return len(article_tokens & transcript_tokens) / max(1, min(len(article_tokens), len(transcript_tokens)))


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z'-]{3,}", text.lower())
        if token not in _STOPWORDS
    }


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text or ""))


def _has_voice_markers(text: str) -> bool:
    lowered = f" {text.lower()} "
    return any(marker in lowered for marker in (" i ", " we ", " my ", " our ", " me "))


def _string_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Iterable):
        return [str(item) for item in value if str(item).strip()]
    return []
