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
