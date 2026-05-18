"""Deterministic advisory scorecards for generated outputs."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

_STOPWORDS = {"about", "after", "again", "also", "because", "been", "being", "from", "have", "into", "just", "more", "most", "that", "their", "there", "these", "this", "through", "with", "when", "where", "which", "while", "will", "your"}
_OUTPUT_ALIASES = {
    "social": "social_content",
    "source_receipts": "source_receipts",
    "songforge_lyric_draft": "songforge",
    "songforge_spoken_word": "songforge",
    "songforge_prompt_pack": "songforge",
}

def build_summary(**data):
    article = str(data.get("article") or "")
    transcript = str(data.get("transcript") or "")
    receipts = _dicts(data.get("source_receipts"))
    flags = _dicts(data.get("fact_check_flags"))
    fact_check_ran = bool(data.get("fact_check_ran"))
    recipe_meta = data.get("recipe_effective_settings") or data.get("recipe") or {}
    output_state = {
        "transcript": bool(transcript.strip()), "wisdom": bool(str(data.get("wisdom") or "").strip()),
        "outline": bool(str(data.get("outline") or "").strip()), "social_content": bool(str(data.get("social_content") or "").strip()),
        "image_prompts": bool(str(data.get("image_prompts") or "").strip()), "article": bool(article.strip()),
        "source_receipts": bool(receipts), "chapters": bool(list(data.get("chapters") or [])),
        "songforge": bool(data.get("songforge")),
    }
    retrieval = _retrieval_counts(data.get("retrieval_inspector"))
    dimensions = [
        _voice(article, retrieval, recipe_meta),
        _grounding(article, transcript, receipts, retrieval, flags, fact_check_ran),
        _usefulness(article, output_state),
        _recipe(recipe_meta, output_state, flags, fact_check_ran),
        _handoff(article, receipts, flags, recipe_meta, list(data.get("exports") or [])),
    ]
    average = round(sum(item["score"] for item in dimensions) / len(dimensions))
    verdict = _verdict(average, dimensions)
    return {"advisory": True, "blocks_save": False, "average_score": average, "verdict": verdict, "verdict_label": verdict.replace("_", " ").title(), "dimensions": dimensions}

def compact_verdict(summary):
    if not isinstance(summary, Mapping):
        return "Scorecard unavailable"
    score = summary.get("average_score")
    label = str(summary.get("verdict_label") or "Review")
    return f"{label} · {int(score)}/100" if isinstance(score, (int, float)) else label

def receipt_for_summary(summary):
    return {"source": "Scorecard", "verdict": compact_verdict(summary), "advisory": "yes" if summary.get("advisory", True) else "no", "blocks_save": "yes" if summary.get("blocks_save") else "no"}

def _voice(article, retrieval, recipe_meta):
    anchors = retrieval.get("voice_anchors") or []
    score = (35 if article.strip() else 0) + (15 if _word_count(article) >= 250 else 0) + (30 if anchors else 0) + (10 if recipe_meta else 0) + (10 if _has_voice_markers(article) else 0)
    notes = ["Draft is present." if article.strip() else "No draft to score."]
    notes.append(f"KB voice anchors used: {', '.join(anchors[:3])}." if anchors else "No KB voice anchors detected; review voice manually.")
    if recipe_meta:
        notes.append("Recipe context is attached.")
    return _dimension("voice", "Voice", score, notes)

def _grounding(article, transcript, receipts, retrieval, flags, fact_check_ran):
    overlap = _overlap_ratio(article, transcript)
    score = (
        (25 if article.strip() and transcript.strip() else 0) + (20 if receipts else 0)
        + (25 if overlap >= 0.18 else 12 if overlap >= 0.08 else 0)
        + (10 if retrieval.get("hits", 0) else 0) + (20 if fact_check_ran and not flags else 0)
        - (min(40, len(flags) * 20) if flags else 0)
    )
    notes = []
    if receipts:
        notes.append(f"{len(receipts)} source receipt(s) attached.")
    notes.append("Draft vocabulary strongly overlaps the source." if overlap >= 0.18 else "Draft has partial source overlap." if overlap >= 0.08 else "Low transcript overlap; inspect source support.")
    if retrieval.get("hits", 0):
        notes.append(f"{retrieval['hits']} retrieval hit(s) available.")
    notes.append("Fact-check ran with no flags." if fact_check_ran and not flags else f"{len(flags)} fact-check flag(s) need review." if flags else "Fact-check was not run.")
    return _dimension("grounding", "Grounding", score, notes)

def _usefulness(article, output_state):
    outputs = [name for name in ("article", "wisdom", "outline", "social_content", "image_prompts", "songforge") if output_state.get(name)]
    words = _word_count(article)
    score = 20 + (len(outputs) * 14) + (10 if words >= 500 else 5 if words else 0) + (5 if output_state.get("chapters") else 0)
    notes = [f"Generated outputs: {', '.join(outputs) or 'none'}."]
    if words:
        notes.append("Article is long enough for publish/review use." if words >= 500 else "Article is brief; useful for handoff or expansion.")
    if output_state.get("chapters"):
        notes.append("Chapters add navigation.")
    return _dimension("usefulness", "Usefulness", score, notes)

def _recipe(recipe_meta, output_state, flags, fact_check_ran):
    expected = _string_list(recipe_meta.get("output_sections")) if isinstance(recipe_meta, Mapping) else []
    checks = _string_list(recipe_meta.get("eval_checks")) if isinstance(recipe_meta, Mapping) else []
    if not expected and not checks:
        return _dimension("recipe_compliance", "Recipe Compliance", 100, ["Manual run; no recipe requirements configured."])
    missing = [section for section in expected if not output_state.get(_OUTPUT_ALIASES.get(section, section), False)]
    missing_checks = []
    if "source_receipts" in checks and not output_state.get("source_receipts"):
        missing_checks.append("source_receipts")
    if "fact_check_flags" in checks and not fact_check_ran:
        missing_checks.append("fact_check_not_run")
    elif "fact_check_flags" in checks and flags:
        missing_checks.append("fact_check_flags_review")
    notes = [f"Missing recipe outputs: {', '.join(missing)}." if missing else "Requested recipe outputs are present."]
    if missing_checks:
        notes.append(f"Eval checks need review: {', '.join(missing_checks)}.")
    elif checks:
        notes.append("Recipe eval checks look satisfied.")
    total = max(1, len(expected) + len(checks))
    return _dimension("recipe_compliance", "Recipe Compliance", round(100 * max(0, total - len(missing) - len(missing_checks)) / total), notes)

def _handoff(article, receipts, flags, recipe_meta, exports):
    targets = _string_list(recipe_meta.get("handoff_targets")) if isinstance(recipe_meta, Mapping) else []
    exported = sorted({str(item.get("kind")) for item in exports if isinstance(item, Mapping) and item.get("kind")})
    score = (30 if article.strip() else 0) + (25 if receipts else 0) + (15 if not flags else 0) + (15 if targets else 5) + (15 if exported else 0)
    notes = []
    if article.strip():
        notes.append("Draft is ready for handoff review.")
    if receipts:
        notes.append("Source receipts travel with the handoff.")
    notes.append("No fact-check flags are currently open." if not flags else "Open fact-check flags should be resolved before publishing.")
    notes.append(f"Handoff targets: {', '.join(targets)}." if targets else "No explicit handoff targets configured.")
    notes.append(f"Recorded exports: {', '.join(exported)}." if exported else "No export has been recorded yet.")
    return _dimension("handoff_readiness", "Handoff Readiness", score, notes)

def _dimension(id_, label, score, notes):
    bounded = max(0, min(100, int(round(score))))
    return {"id": id_, "label": label, "score": bounded, "status": "strong" if bounded >= 80 else "review" if bounded >= 60 else "attention", "notes": notes}

def _verdict(average, dimensions):
    low = min(item["score"] for item in dimensions)
    return "needs_review" if low < 50 else "ready" if average >= 80 and low >= 65 else "review"

def _retrieval_counts(inspector):
    stages = inspector.get("stages") if isinstance(inspector, Mapping) else {}
    hits = [hit for stage_hits in (stages.values() if isinstance(stages, Mapping) else []) for hit in (stage_hits or []) if isinstance(hit, Mapping)]
    anchors = sorted({str(hit.get("doc_name")) for hit in hits if hit.get("role") == "voice_anchor" and hit.get("doc_name")})
    return {"hits": len(hits), "voice_anchors": anchors}

def _overlap_ratio(article, transcript):
    article_tokens = _tokens(article)
    transcript_tokens = _tokens(transcript)
    return 0.0 if not article_tokens or not transcript_tokens else len(article_tokens & transcript_tokens) / max(1, min(len(article_tokens), len(transcript_tokens)))

def _tokens(text):
    return {token for token in re.findall(r"[a-zA-Z][a-zA-Z'-]{3,}", text.lower()) if token not in _STOPWORDS}

def _dicts(value):
    return [dict(item) for item in value or [] if isinstance(item, Mapping)]

def _string_list(value):
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value if str(item).strip()] if isinstance(value, Iterable) else []

def _word_count(text):
    return len(re.findall(r"\b\w+\b", text or ""))

def _has_voice_markers(text):
    return any(marker in f" {text.lower()} " for marker in (" i ", " we ", " my ", " our ", " me "))
