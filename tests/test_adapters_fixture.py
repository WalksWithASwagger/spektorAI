"""Tests for fixture-backed adapters used by browser E2E smoke."""

from __future__ import annotations

import json

import pytest

from whisperforge_core import adapters as adapters_mod


def _fixture_payload() -> dict:
    return {
        "transcription": {
            "text": "fixture transcript",
            "segments": [],
            "language": "en",
        },
        "pipeline_result": {
            "wisdom": "fixture wisdom",
            "outline": "fixture outline",
            "social_posts": "fixture social",
            "image_prompts": "fixture prompts",
            "article": "# Fixture article",
        },
        "notion_url": "https://notion.so/fixture",
    }


def test_get_adapters_uses_fixture_bundle_when_env_set(monkeypatch, tmp_path):
    fixture_path = tmp_path / "browser-e2e-fixture.json"
    fixture_path.write_text(json.dumps(_fixture_payload()), encoding="utf-8")
    monkeypatch.setenv("WHISPERFORGE_E2E_FIXTURE_PATH", str(fixture_path))

    adapters = adapters_mod.get_adapters()
    details = adapters.transcriber.transcribe_detailed(b"", suffix=".mp3")
    assert details.text == "fixture transcript"
    assert details.language == "en"

    seen_stages: list[str] = []

    def checkpoint(stage: str, payload: dict) -> None:
        seen_stages.append(stage)

    result = adapters.processor.run_pipeline(
        transcript="ignored",
        provider="anthropic",
        model="claude-haiku-4-5",
        checkpoint=checkpoint,
    )
    assert result.article == "# Fixture article"
    assert "wisdom" in seen_stages
    assert adapters.storage.save(None) == "https://notion.so/fixture"


def test_get_adapters_fixture_missing_file_raises(monkeypatch, tmp_path):
    missing_path = tmp_path / "missing-fixture.json"
    monkeypatch.setenv("WHISPERFORGE_E2E_FIXTURE_PATH", str(missing_path))

    with pytest.raises(FileNotFoundError):
        adapters_mod.get_adapters()
