import io
import os
from types import SimpleNamespace

from fastapi.testclient import TestClient

from services.processing import service as processing_service
from services.storage import service as storage_service
from services.transcription import service as transcription_service
from whisperforge_core import audio
from whisperforge_core import pipeline


HEADERS = {"X-API-Key": "dummy"}


def test_transcription_service_returns_detailed_payload(monkeypatch):
    def fake_transcribe_audio_detailed(_path):
        return audio.TranscriptionDetails(
            text="Transcript body",
            segments=[{"start": 0.0, "end": 1.2, "text": "hello"}],
            language="en",
        )

    monkeypatch.setattr(
        transcription_service.audio,
        "transcribe_audio_detailed",
        fake_transcribe_audio_detailed,
    )
    client = TestClient(transcription_service.app)
    response = client.post(
        "/transcribe",
        files={"file": ("sample.wav", b"fake-audio", "audio/wav")},
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {
        "text": "Transcript body",
        "segments": [{"start": 0.0, "end": 1.2, "text": "hello"}],
        "language": "en",
        "filename": "sample.wav",
    }


def test_transcription_service_copy_upload_uses_file_stream_not_async_read():
    async def fail_read():
        raise AssertionError("UploadFile.read should not be used for spooling")

    upload = SimpleNamespace(file=io.BytesIO(b"fake-audio"), read=fail_read)
    path = transcription_service._copy_upload_to_temp(upload, ".wav")
    try:
        with open(path, "rb") as handle:
            assert handle.read() == b"fake-audio"
    finally:
        os.unlink(path)


def test_processing_pipeline_accepts_modern_options_and_returns_full_result(monkeypatch):
    captured = {}

    def fake_run(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return pipeline.PipelineResult(
            wisdom="wisdom",
            outline="outline",
            social_posts="social",
            image_prompts="prompts",
            article="article",
            raw_transcript="raw",
            cleaned_transcript="clean",
            chapters=[{"title": "Intro"}],
            article_draft="draft",
            article_critique="critique",
            fact_check_flags=[{"claim": "x", "issue": "y"}],
            generated_images=[{"path": "/tmp/a.png", "prompt": "p", "succeeded": True}],
            article_compare="compare",
            compare_label="OpenAI gpt-4o",
            persona_articles=[{"name": "Direct", "text": "persona"}],
            songforge={"lyric_draft": "lyric"},
        )

    monkeypatch.setattr(processing_service.pipeline, "run", fake_run)
    client = TestClient(processing_service.app)

    payload = {
        "transcript": "raw",
        "provider": "Anthropic",
        "model": "claude-haiku-4-5",
        "prompts": {"article_writing": "custom"},
        "knowledge_base": {"voice": "notes"},
        "cleanup": False,
        "chapters": True,
        "segments": [{"text": "raw", "start": 0.0}],
        "agentic": True,
        "fact_check": True,
        "generate_images": True,
        "image_style": "editorial",
        "image_aspect_ratio": "1:1",
        "image_model": "gemini-image",
        "image_output_dir": "/tmp/images",
        "article_length_words": 900,
        "user": "kk",
        "rag_mode": "retrieval",
        "compare_provider": "OpenAI",
        "compare_model": "gpt-4o",
        "personas": ["Direct"],
        "recipe": None,
    }
    response = client.post("/pipeline", json=payload, headers=HEADERS)

    assert response.status_code == 200
    assert captured["args"] == ("raw", "Anthropic", "claude-haiku-4-5")
    assert captured["kwargs"] == {
        "prompts": {"article_writing": "custom"},
        "knowledge_base": {"voice": "notes"},
        "cleanup": False,
        "chapters": True,
        "segments": [{"text": "raw", "start": 0.0}],
        "agentic": True,
        "fact_check": True,
        "generate_images": True,
        "image_style": "editorial",
        "image_aspect_ratio": "1:1",
        "image_model": "gemini-image",
        "image_output_dir": "/tmp/images",
        "article_length_words": 900,
        "user": "kk",
        "rag_mode": "retrieval",
        "compare_provider": "OpenAI",
        "compare_model": "gpt-4o",
        "personas": ["Direct"],
        "recipe": None,
    }
    assert response.json() == {
        "wisdom": "wisdom",
        "outline": "outline",
        "social_posts": "social",
        "image_prompts": "prompts",
        "article": "article",
        "raw_transcript": "raw",
        "cleaned_transcript": "clean",
        "chapters": [{"title": "Intro"}],
        "article_draft": "draft",
        "article_critique": "critique",
        "fact_check_flags": [{"claim": "x", "issue": "y"}],
        "generated_images": [{"path": "/tmp/a.png", "prompt": "p", "succeeded": True}],
        "article_compare": "compare",
        "compare_label": "OpenAI gpt-4o",
        "persona_articles": [{"name": "Direct", "text": "persona"}],
        "songforge": {"lyric_draft": "lyric"},
    }


def test_processing_pipeline_rejects_unknown_fields():
    client = TestClient(processing_service.app)
    response = client.post(
        "/pipeline",
        json={
            "transcript": "raw",
            "provider": "Anthropic",
            "model": "claude-haiku-4-5",
            "surprise": True,
        },
        headers=HEADERS,
    )

    assert response.status_code == 422


def test_processing_generate_accepts_modern_llm_options(monkeypatch):
    captured = {}

    def fake_generate(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return "generated"

    monkeypatch.setattr(processing_service.llm, "generate", fake_generate)
    client = TestClient(processing_service.app)
    response = client.post(
        "/generate",
        json={
            "content_type": "article_writing",
            "context": {"transcript": "t", "wisdom": "w", "outline": "o"},
            "provider": "Anthropic",
            "model": "claude-haiku-4-5",
            "prompt": "prompt",
            "knowledge_base": {"voice": "notes"},
            "max_tokens": 1234,
            "user": "kk",
            "rag_mode": "retrieval",
        },
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {"result": "generated"}
    assert captured["args"] == (
        "article_writing",
        {"transcript": "t", "wisdom": "w", "outline": "o"},
        "Anthropic",
        "claude-haiku-4-5",
    )
    assert captured["kwargs"] == {
        "prompt": "prompt",
        "knowledge_base": {"voice": "notes"},
        "max_tokens": 1234,
        "user": "kk",
        "rag_mode": "retrieval",
    }


def test_storage_save_accepts_modern_bundle_fields(monkeypatch):
    captured = {}

    def fake_create_page(bundle, database_id=None):
        captured["bundle"] = bundle
        captured["database_id"] = database_id
        return "https://notion.so/page"

    monkeypatch.setattr(storage_service.notion, "create_page", fake_create_page)
    client = TestClient(storage_service.app)
    response = client.post(
        "/save",
        json={
            "title": "Title",
            "transcript": "transcript",
            "wisdom": "wisdom",
            "outline": "outline",
            "social_content": "social",
            "image_prompts": "prompts",
            "article": "article",
            "summary": "summary",
            "tags": ["tag"],
            "audio_filename": "audio.mp3",
            "models_used": ["model"],
            "database_id": "db",
            "chapters": [{"title": "Intro"}],
            "article_compare": "compare",
            "compare_label": "OpenAI gpt-4o",
            "persona_articles": [{"name": "Direct", "text": "persona"}],
            "article_critique": "critique",
            "fact_check_flags": [{"claim": "x", "issue": "y"}],
            "fact_check_ran": True,
            "run_metrics": {"total_usd": 0.01},
            "source_receipts": [{"source": "Transcript", "sha256": "abc"}],
        },
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {"url": "https://notion.so/page"}
    assert captured["database_id"] == "db"
    bundle = captured["bundle"]
    assert bundle.chapters == [{"title": "Intro"}]
    assert bundle.article_compare == "compare"
    assert bundle.compare_label == "OpenAI gpt-4o"
    assert bundle.persona_articles == [{"name": "Direct", "text": "persona"}]
    assert bundle.article_critique == "critique"
    assert bundle.fact_check_flags == [{"claim": "x", "issue": "y"}]
    assert bundle.fact_check_ran is True
    assert bundle.run_metrics == {"total_usd": 0.01}
    assert bundle.source_receipts == [{"source": "Transcript", "sha256": "abc"}]


def test_storage_save_rejects_unknown_fields():
    client = TestClient(storage_service.app)
    response = client.post(
        "/save",
        json={"title": "Title", "surprise": True},
        headers=HEADERS,
    )

    assert response.status_code == 422
