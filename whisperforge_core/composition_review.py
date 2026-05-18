"""Evidence summary helpers for the composition review surface."""

from __future__ import annotations

from typing import Any, Iterable, Mapping


def build_summary(
    *,
    source_receipts: Iterable[Mapping[str, Any]] | None = None,
    retrieval_inspector: Mapping[str, Any] | None = None,
    fact_check_flags: Iterable[Mapping[str, Any]] | None = None,
    article_critique: str | None = None,
    article_compare: str | None = None,
    persona_articles: Iterable[Mapping[str, Any]] | None = None,
    chapters: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    receipts = [dict(item) for item in source_receipts or [] if isinstance(item, Mapping)]
    flags = [dict(item) for item in fact_check_flags or [] if isinstance(item, Mapping)]
    personas = [dict(item) for item in persona_articles or [] if isinstance(item, Mapping)]
    quotes = _receipt_quotes(receipts) + _chapter_quotes(chapters) + _retrieval_quotes(retrieval_inspector)
    retrieval = _retrieval_summary(retrieval_inspector)
    return {
        "source_count": len(receipts),
        "sources": [_receipt_label(item) for item in receipts][:12],
        "quote_count": len(quotes),
        "quotes": quotes[:8],
        "claim_flag_count": len(flags),
        "claim_flags": [
            {"claim": str(flag.get("claim", "")), "issue": str(flag.get("issue", ""))}
            for flag in flags
        ],
        "has_revision_notes": bool((article_critique or "").strip()),
        "compare_variant_count": 1 if article_compare else 0,
        "persona_variant_count": len(personas),
        "persona_variants": [
            str(item.get("name") or "Persona")
            for item in personas
        ],
        "retrieval": retrieval,
    }


def receipt_for_summary(summary: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source": "Composition review",
        "sources": summary.get("source_count", 0),
        "quotes": summary.get("quote_count", 0),
        "claim_flags": summary.get("claim_flag_count", 0),
        "revision_notes": "yes" if summary.get("has_revision_notes") else "no",
        "compare_variants": summary.get("compare_variant_count", 0),
        "persona_variants": summary.get("persona_variant_count", 0),
    }


def _receipt_quotes(receipts: list[dict[str, Any]]) -> list[dict[str, str]]:
    quotes = []
    for receipt in receipts:
        excerpt = str(receipt.get("excerpt") or "").strip()
        if not excerpt:
            continue
        quotes.append({"label": _receipt_label(receipt), "quote": excerpt[:320]})
    return quotes


def _chapter_quotes(chapters: Iterable[Mapping[str, Any]] | None) -> list[dict[str, str]]:
    quotes = []
    for chapter in chapters or []:
        if not isinstance(chapter, Mapping):
            continue
        quote = str(chapter.get("start_quote") or "").strip()
        if not quote:
            continue
        label = str(chapter.get("title") or "Chapter")
        quotes.append({"label": label, "quote": quote[:320]})
    return quotes


def _retrieval_quotes(inspector: Mapping[str, Any] | None) -> list[dict[str, str]]:
    quotes = []
    if not isinstance(inspector, Mapping):
        return quotes
    stages = inspector.get("stages") or {}
    if not isinstance(stages, Mapping):
        return quotes
    seen: set[str] = set()
    for stage, hits in stages.items():
        for hit in hits or []:
            if not isinstance(hit, Mapping):
                continue
            excerpt = str(hit.get("excerpt") or "").strip()
            if not excerpt or excerpt in seen:
                continue
            seen.add(excerpt)
            label = str(hit.get("doc_name") or stage or "Knowledge")
            quotes.append({"label": label, "quote": excerpt[:320]})
            if len(quotes) >= 4:
                return quotes
    return quotes


def _retrieval_summary(inspector: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(inspector, Mapping):
        return {"engaged": False, "hits": 0, "voice_anchors": []}
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
    return {
        "engaged": bool(inspector.get("engaged")),
        "hits": len(hits),
        "voice_anchors": anchors,
    }


def _receipt_label(receipt: Mapping[str, Any]) -> str:
    return str(
        receipt.get("label")
        or receipt.get("title")
        or receipt.get("name")
        or receipt.get("source")
        or "Source"
    )
