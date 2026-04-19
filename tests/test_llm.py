"""Tests for whisperforge_core.llm.generate — dispatch, prompt composition,
and provider routing. Mocks the OpenAI / Anthropic clients so no network
calls happen."""

from unittest.mock import MagicMock, patch

import pytest

from whisperforge_core import llm


@pytest.fixture
def mock_openai(monkeypatch):
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content="openai result"))]
    client = MagicMock()
    client.chat.completions.create.return_value = response
    monkeypatch.setattr(llm, "_openai", lambda: client)
    return client


@pytest.fixture
def mock_anthropic(monkeypatch):
    response = MagicMock()
    response.content = [MagicMock(text="anthropic result")]
    client = MagicMock()
    client.messages.create.return_value = response
    monkeypatch.setattr(llm, "_anthropic", lambda: client)
    return client


class TestDispatch:
    def test_unknown_content_type_raises(self):
        with pytest.raises(ValueError, match="Unknown content_type"):
            llm.generate("not_a_real_type", {}, "OpenAI", "gpt-4")

    def test_openai_routing(self, mock_openai):
        result = llm.generate(
            "wisdom_extraction",
            {"transcript": "some text"},
            "OpenAI",
            "gpt-4",
        )
        assert result == "openai result"
        mock_openai.chat.completions.create.assert_called_once()
        call = mock_openai.chat.completions.create.call_args
        assert call.kwargs["model"] == "gpt-4"
        messages = call.kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "some text" in messages[1]["content"]

    def test_anthropic_routing(self, mock_anthropic):
        result = llm.generate(
            "wisdom_extraction",
            {"transcript": "body"},
            "Anthropic",
            "claude-3-sonnet-20240229",
        )
        assert result == "anthropic result"
        mock_anthropic.messages.create.assert_called_once()

    def test_unsupported_provider_returns_none(self, mock_openai):
        # Logged + None returned, not raised, because generate() catches.
        result = llm.generate(
            "wisdom_extraction",
            {"transcript": "body"},
            "NotAProvider",
            "whatever",
        )
        assert result is None


class TestPromptComposition:
    def test_knowledge_base_prepended_to_system(self, mock_openai):
        kb = {"Voice": "be friendly"}
        llm.generate(
            "wisdom_extraction",
            {"transcript": "body"},
            "OpenAI",
            "gpt-4",
            prompt="extract insights",
            knowledge_base=kb,
        )
        system = mock_openai.chat.completions.create.call_args.kwargs["messages"][0]["content"]
        assert "be friendly" in system
        assert "extract insights" in system

    def test_no_kb_uses_plain_prompt(self, mock_openai):
        llm.generate(
            "wisdom_extraction",
            {"transcript": "body"},
            "OpenAI",
            "gpt-4",
            prompt="just this prompt",
        )
        system = mock_openai.chat.completions.create.call_args.kwargs["messages"][0]["content"]
        assert system == "just this prompt"

    def test_default_prompt_used_when_none_supplied(self, mock_openai):
        llm.generate(
            "wisdom_extraction",
            {"transcript": "body"},
            "OpenAI",
            "gpt-4",
        )
        system = mock_openai.chat.completions.create.call_args.kwargs["messages"][0]["content"]
        assert "insights" in system.lower() or "wisdom" in system.lower()


class TestContextBuilders:
    def test_outline_context_combines_transcript_and_wisdom(self, mock_openai):
        llm.generate(
            "outline_creation",
            {"transcript": "THE TRANSCRIPT", "wisdom": "THE WISDOM"},
            "OpenAI",
            "gpt-4",
        )
        user = mock_openai.chat.completions.create.call_args.kwargs["messages"][1]["content"]
        assert "THE TRANSCRIPT" in user
        assert "THE WISDOM" in user

    def test_article_max_tokens_is_2500(self, mock_openai):
        llm.generate(
            "article_writing",
            {"transcript": "t", "wisdom": "w", "outline": "o"},
            "OpenAI",
            "gpt-4",
        )
        assert mock_openai.chat.completions.create.call_args.kwargs["max_tokens"] == 2500

    def test_social_max_tokens_is_1000(self, mock_openai):
        llm.generate(
            "social_media",
            {"wisdom": "w", "outline": "o"},
            "OpenAI",
            "gpt-4",
        )
        assert mock_openai.chat.completions.create.call_args.kwargs["max_tokens"] == 1000

    def test_transcript_cleanup_passes_raw_transcript_as_user_content(self, mock_openai):
        """Cleanup stage feeds the raw transcript directly — no framing phrase —
        so the model doesn't hallucinate one into its output."""
        llm.generate(
            "transcript_cleanup",
            {"transcript": "uh, hi, you know?"},
            "OpenAI",
            "gpt-4o-mini",
        )
        user_msg = mock_openai.chat.completions.create.call_args.kwargs["messages"][1]["content"]
        assert user_msg == "uh, hi, you know?"

    def test_transcript_cleanup_max_tokens_is_4000(self, mock_openai):
        llm.generate(
            "transcript_cleanup",
            {"transcript": "x"},
            "OpenAI",
            "gpt-4o-mini",
        )
        assert mock_openai.chat.completions.create.call_args.kwargs["max_tokens"] == 4000


class TestAnthropicPromptCaching:
    """The Anthropic branch splits KB + per-stage prompt into separate system
    blocks so the KB (long, stable) caches across the 5-stage pipeline."""

    def test_kb_and_prompt_are_separate_blocks_with_cache_control_on_kb(self, mock_anthropic):
        llm.generate(
            "wisdom_extraction",
            {"transcript": "body"},
            "Anthropic",
            "claude-haiku-4-5",
            prompt="stage-specific instructions",
            knowledge_base={"Voice": "friendly"},
        )
        system_blocks = mock_anthropic.messages.create.call_args.kwargs["system"]
        assert isinstance(system_blocks, list)
        assert len(system_blocks) == 2
        kb_block, prompt_block = system_blocks
        # KB comes first and is cacheable
        assert "friendly" in kb_block["text"]
        assert kb_block["cache_control"] == {"type": "ephemeral"}
        # Prompt body comes second and is NOT cached (so it can vary per stage)
        assert "stage-specific" in prompt_block["text"]
        assert "cache_control" not in prompt_block

    def test_no_kb_produces_single_block_no_cache_control(self, mock_anthropic):
        llm.generate(
            "wisdom_extraction",
            {"transcript": "body"},
            "Anthropic",
            "claude-haiku-4-5",
            prompt="just the prompt",
        )
        system_blocks = mock_anthropic.messages.create.call_args.kwargs["system"]
        assert system_blocks == [{"type": "text", "text": "just the prompt"}]
