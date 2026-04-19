"""Tests for the agentic article drafting flow.

Patches ``llm.generate`` at the pipeline boundary so we can assert exactly
which content_types get called in which order without touching network.
"""

from unittest.mock import MagicMock

import pytest

from whisperforge_core import pipeline


@pytest.fixture
def mock_llm(monkeypatch):
    """Return a mock that records every generate() call it receives.

    Returns canned strings keyed by content_type so the pipeline sees
    plausible non-empty outputs at each stage.
    """
    canned = {
        "transcript_cleanup": "cleaned transcript",
        "chapters": '{"chapters":[]}',  # parsed by generate_chapters directly
        "chapters_timestamped": '{"chapters":[]}',
        "wisdom_extraction": "wisdom output",
        "outline_creation": "outline output",
        "social_media": "social output",
        "image_prompts": "image output",
        "article_writing": "DRAFT VERSION",
        "article_critique": "- voice is off\n- add examples",
        "article_revise": "REVISED VERSION",
        "article_fact_check": '{"flags":[]}',
    }
    calls = []

    def fake_generate(content_type, context, provider, model, **kwargs):
        calls.append((content_type, dict(context)))
        return canned.get(content_type, "")

    from whisperforge_core import llm as llm_mod
    monkeypatch.setattr(llm_mod, "generate", fake_generate)
    return calls


class TestAgenticOff:
    def test_single_pass_when_agentic_false(self, mock_llm):
        result = pipeline.run(
            "raw transcript", "Anthropic", "claude-haiku-4-5",
            cleanup=False, chapters=False, agentic=False,
        )
        types = [c[0] for c in mock_llm]
        assert "article_writing" in types
        assert "article_critique" not in types
        assert "article_revise" not in types
        assert result.article == "DRAFT VERSION"
        assert result.article_draft == "DRAFT VERSION"
        assert result.article_critique is None

    def test_no_fact_check_when_flag_false(self, mock_llm):
        result = pipeline.run(
            "raw transcript", "Anthropic", "claude-haiku-4-5",
            cleanup=False, chapters=False, fact_check=False,
        )
        assert "article_fact_check" not in [c[0] for c in mock_llm]
        assert result.fact_check_flags == []


class TestAgenticOn:
    def test_agentic_runs_critique_and_revise(self, mock_llm):
        result = pipeline.run(
            "raw transcript", "Anthropic", "claude-haiku-4-5",
            cleanup=False, chapters=False, agentic=True,
        )
        order = [c[0] for c in mock_llm]
        assert order.index("article_writing") < order.index("article_critique")
        assert order.index("article_critique") < order.index("article_revise")
        assert result.article == "REVISED VERSION"
        assert result.article_draft == "DRAFT VERSION"
        assert result.article_critique == "- voice is off\n- add examples"

    def test_critique_receives_draft_plus_source(self, mock_llm):
        pipeline.run(
            "my transcript here", "Anthropic", "claude-haiku-4-5",
            cleanup=False, chapters=False, agentic=True,
        )
        critique_call = next(c for c in mock_llm if c[0] == "article_critique")
        ctx = critique_call[1]
        assert ctx["article"] == "DRAFT VERSION"
        assert ctx["transcript"] == "my transcript here"

    def test_revise_receives_draft_critique_and_source(self, mock_llm):
        pipeline.run(
            "my transcript here", "Anthropic", "claude-haiku-4-5",
            cleanup=False, chapters=False, agentic=True,
        )
        revise_call = next(c for c in mock_llm if c[0] == "article_revise")
        ctx = revise_call[1]
        assert ctx["article"] == "DRAFT VERSION"
        assert ctx["critique"] == "- voice is off\n- add examples"
        assert ctx["transcript"] == "my transcript here"


class TestFactCheck:
    def test_fact_check_runs_when_flag_true(self, mock_llm):
        result = pipeline.run(
            "raw transcript", "Anthropic", "claude-haiku-4-5",
            cleanup=False, chapters=False, fact_check=True,
        )
        assert "article_fact_check" in [c[0] for c in mock_llm]
        assert result.fact_check_flags == []

    def test_fact_check_flags_are_parsed(self, monkeypatch):
        canned = {
            "article_writing": "SOME ARTICLE",
            "article_fact_check": (
                '{"flags":[{"claim":"The sky is green","issue":"Transcript says blue."}]}'
            ),
        }

        def fake_generate(ct, ctx, *a, **k):
            return canned.get(ct, "")

        from whisperforge_core import llm as llm_mod
        monkeypatch.setattr(llm_mod, "generate", fake_generate)
        result = pipeline.run(
            "transcript", "Anthropic", "claude-haiku-4-5",
            cleanup=False, chapters=False, fact_check=True,
        )
        assert len(result.fact_check_flags) == 1
        assert result.fact_check_flags[0]["claim"] == "The sky is green"
        assert "blue" in result.fact_check_flags[0]["issue"].lower()

    def test_fact_check_runs_against_revised_article_when_agentic(self, mock_llm):
        """Fact-check should see the post-revision article, not the draft."""
        pipeline.run(
            "raw", "Anthropic", "claude-haiku-4-5",
            cleanup=False, chapters=False, agentic=True, fact_check=True,
        )
        fc_call = next(c for c in mock_llm if c[0] == "article_fact_check")
        assert fc_call[1]["article"] == "REVISED VERSION"


class TestFactCheckParser:
    def test_empty_output_returns_empty(self):
        assert pipeline._parse_fact_check(None) == []
        assert pipeline._parse_fact_check("") == []

    def test_markdown_fences_stripped(self):
        raw = '```json\n{"flags":[{"claim":"x","issue":"y"}]}\n```'
        flags = pipeline._parse_fact_check(raw)
        assert flags == [{"claim": "x", "issue": "y"}]

    def test_malformed_json_returns_empty(self):
        assert pipeline._parse_fact_check("not json at all") == []
        assert pipeline._parse_fact_check("{not:valid}") == []

    def test_flags_without_claim_are_dropped(self):
        raw = '{"flags":[{"issue":"missing claim"},{"claim":"kept","issue":"ok"}]}'
        flags = pipeline._parse_fact_check(raw)
        assert len(flags) == 1
        assert flags[0]["claim"] == "kept"
