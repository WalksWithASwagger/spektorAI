"""Tests for deterministic advisory scorecards."""

from whisperforge_core import scorecards


def test_scorecard_returns_all_advisory_dimensions_without_credentials():
    summary = scorecards.build_summary(
        article=(
            "I think taste is leverage when the final piece keeps source "
            "evidence, useful handoff notes, and a clear editorial point."
        ),
        transcript=(
            "Taste is leverage. The final piece should keep source evidence "
            "and become useful enough for handoff."
        ),
        wisdom="Taste is leverage.",
        outline="Hook, evidence, handoff.",
        social_content="Taste is leverage when receipts travel with the work.",
        source_receipts=[{"source": "Transcript", "excerpt": "Taste is leverage."}],
        retrieval_inspector={
            "stages": {
                "article_writing": [
                    {
                        "role": "voice_anchor",
                        "doc_name": "voice.md",
                        "excerpt": "Write like a field note.",
                    }
                ]
            }
        },
        fact_check_ran=True,
        recipe_effective_settings={
            "recipe_id": "article_with_receipts",
            "recipe_name": "Article with receipts",
            "output_sections": ["article", "wisdom", "outline", "social_content", "source_receipts"],
            "eval_checks": ["source_receipts"],
            "handoff_targets": ["markdown"],
        },
    )

    assert summary["advisory"] is True
    assert summary["blocks_save"] is False
    assert {item["id"] for item in summary["dimensions"]} == {
        "voice",
        "grounding",
        "usefulness",
        "recipe_compliance",
        "handoff_readiness",
    }
    assert summary["average_score"] >= 70
    assert "Scorecard" in scorecards.receipt_for_summary(summary)["source"]


def test_recipe_compliance_flags_missing_outputs():
    summary = scorecards.build_summary(
        article="A short draft.",
        transcript="A short source.",
        recipe_effective_settings={
            "output_sections": ["article", "source_receipts", "social_content"],
            "eval_checks": ["source_receipts"],
        },
    )

    recipe = next(
        item for item in summary["dimensions"]
        if item["id"] == "recipe_compliance"
    )
    assert recipe["score"] < 70
    assert any("Missing recipe outputs" in note for note in recipe["notes"])


def test_fact_check_flags_lower_grounding_and_handoff():
    clean = scorecards.build_summary(
        article="Source-backed draft with useful evidence.",
        transcript="Source-backed draft with useful evidence.",
        source_receipts=[{"source": "Transcript"}],
        fact_check_ran=True,
    )
    flagged = scorecards.build_summary(
        article="Source-backed draft with useful evidence.",
        transcript="Source-backed draft with useful evidence.",
        source_receipts=[{"source": "Transcript"}],
        fact_check_ran=True,
        fact_check_flags=[{"claim": "unsupported", "issue": "not in source"}],
    )

    clean_grounding = next(item for item in clean["dimensions"] if item["id"] == "grounding")
    flagged_grounding = next(item for item in flagged["dimensions"] if item["id"] == "grounding")
    clean_handoff = next(item for item in clean["dimensions"] if item["id"] == "handoff_readiness")
    flagged_handoff = next(item for item in flagged["dimensions"] if item["id"] == "handoff_readiness")

    assert flagged_grounding["score"] < clean_grounding["score"]
    assert flagged_handoff["score"] < clean_handoff["score"]
