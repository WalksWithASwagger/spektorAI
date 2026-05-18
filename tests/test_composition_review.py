"""Tests for composition review evidence summaries."""

from whisperforge_core import composition_review


def test_review_summary_counts_sources_flags_variants_and_retrieval():
    summary = composition_review.build_summary(
        source_receipts=[
            {
                "source": "Transcript",
                "excerpt": "Taste is leverage when it is grounded in evidence.",
            },
            {"source": "Knowledge retrieval", "hits": 3},
        ],
        retrieval_inspector={
            "engaged": True,
            "stages": {
                "article_writing": [
                    {
                        "role": "voice_anchor",
                        "doc_name": "voice.md",
                        "excerpt": "Write like a field note.",
                    },
                    {
                        "role": "context",
                        "doc_name": "context.md",
                        "excerpt": "Ground claims in the source.",
                    },
                ]
            },
        },
        fact_check_flags=[{"claim": "The sky is red", "issue": "Source says blue."}],
        article_critique="- tighten the ending",
        article_compare="alternate draft",
        persona_articles=[{"name": "Operator", "text": "variant"}],
        chapters=[{"title": "Opening", "start_quote": "Let's begin with the source."}],
    )

    assert summary["source_count"] == 2
    assert summary["claim_flag_count"] == 1
    assert summary["has_revision_notes"] is True
    assert summary["compare_variant_count"] == 1
    assert summary["persona_variant_count"] == 1
    assert summary["retrieval"]["hits"] == 2
    assert summary["retrieval"]["voice_anchors"] == ["voice.md"]
    assert any("Taste is leverage" in item["quote"] for item in summary["quotes"])
    assert any("Let's begin" in item["quote"] for item in summary["quotes"])


def test_receipt_for_summary_preserves_review_counts_for_exports():
    receipt = composition_review.receipt_for_summary({
        "source_count": 3,
        "quote_count": 4,
        "claim_flag_count": 1,
        "has_revision_notes": True,
        "compare_variant_count": 1,
        "persona_variant_count": 2,
    })

    assert receipt == {
        "source": "Composition review",
        "sources": 3,
        "quotes": 4,
        "claim_flags": 1,
        "revision_notes": "yes",
        "compare_variants": 1,
        "persona_variants": 2,
    }
