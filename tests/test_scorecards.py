"""Tests for deterministic advisory scorecards."""

from whisperforge_core import scorecards


def test_scorecard_returns_all_advisory_dimensions_without_credentials():
    summary = scorecards.build_summary(
        article="I think taste is leverage when source evidence travels with the handoff.",
        transcript="Taste is leverage. Source evidence should travel with the handoff.",
        wisdom="Taste is leverage.",
        outline="Hook, evidence, handoff.",
        social_content="Receipts travel with the work.",
        source_receipts=[{"source": "Transcript", "excerpt": "Taste is leverage."}],
        retrieval_inspector={
            "stages": {"article_writing": [{"role": "voice_anchor", "doc_name": "voice.md"}]}
        },
        fact_check_ran=True,
        recipe_effective_settings={
            "recipe_id": "article_with_receipts",
            "output_sections": ["article", "wisdom", "outline", "social_content", "source_receipts"],
            "eval_checks": ["source_receipts", "fact_check_flags"],
            "handoff_targets": ["markdown"],
        },
    )

    assert summary["advisory"] is True
    assert summary["blocks_save"] is False
    assert {item["id"] for item in summary["dimensions"]} == {
        "voice", "grounding", "usefulness", "recipe_compliance", "handoff_readiness",
    }
    assert summary["average_score"] >= 70
    assert scorecards.receipt_for_summary(summary)["source"] == "Scorecard"


def test_missing_recipe_outputs_and_fact_flags_lower_scores():
    summary = scorecards.build_summary(
        article="A short draft.",
        transcript="A short source.",
        fact_check_ran=True,
        fact_check_flags=[{"claim": "unsupported", "issue": "not in source"}],
        recipe_effective_settings={
            "output_sections": ["article", "source_receipts", "social_content"],
            "eval_checks": ["source_receipts", "fact_check_flags"],
        },
    )

    by_id = {item["id"]: item for item in summary["dimensions"]}
    assert by_id["recipe_compliance"]["score"] < 70
    assert by_id["grounding"]["score"] < 70
    assert by_id["handoff_readiness"]["score"] < 70
