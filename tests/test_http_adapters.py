from whisperforge_core import http_adapters, notion


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_http_transcribe_detailed_round_trips_segments_and_language(monkeypatch):
    calls = []

    def fake_post(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        return FakeResponse({
            "text": "Transcript body",
            "segments": [{"start": 0.0, "end": 1.2, "text": "hello"}],
            "language": "en",
        })

    monkeypatch.setattr(http_adapters.requests, "post", fake_post)

    details = http_adapters.HttpTranscriber().transcribe_detailed(
        b"fake-audio",
        suffix=".wav",
    )

    assert details.text == "Transcript body"
    assert details.segments == [{"start": 0.0, "end": 1.2, "text": "hello"}]
    assert details.language == "en"
    assert calls[0]["args"][0].endswith("/transcribe")
    assert calls[0]["kwargs"]["files"]["file"][0] == "upload.wav"


def test_http_generate_forwards_modern_options(monkeypatch):
    calls = []

    def fake_post(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        return FakeResponse({"result": "generated"})

    monkeypatch.setattr(http_adapters.requests, "post", fake_post)

    result = http_adapters.HttpProcessor().generate(
        "article_writing",
        {"transcript": "t"},
        "Anthropic",
        "claude-haiku-4-5",
        prompt="prompt",
        knowledge_base={"voice": "notes"},
        max_tokens=1200,
        user="kk",
        rag_mode="retrieval",
    )

    assert result == "generated"
    assert calls[0]["kwargs"]["json"] == {
        "content_type": "article_writing",
        "context": {"transcript": "t"},
        "provider": "Anthropic",
        "model": "claude-haiku-4-5",
        "prompt": "prompt",
        "knowledge_base": {"voice": "notes"},
        "max_tokens": 1200,
        "user": "kk",
        "rag_mode": "retrieval",
    }


def test_http_pipeline_round_trips_modern_options_and_result(monkeypatch):
    calls = []
    response_payload = {
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
        "generated_images": [
            {"path": "/tmp/a.png", "prompt": "p", "succeeded": True}
        ],
        "article_compare": "compare",
        "compare_label": "OpenAI gpt-4o",
        "persona_articles": [{"name": "Direct", "text": "persona"}],
        "songforge": {"lyric_draft": "lyric"},
    }

    def fake_post(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        return FakeResponse(response_payload)

    monkeypatch.setattr(http_adapters.requests, "post", fake_post)

    result = http_adapters.HttpProcessor().run_pipeline(
        "raw",
        "Anthropic",
        "claude-haiku-4-5",
        prompts={"article_writing": "custom"},
        knowledge_base={"voice": "notes"},
        cleanup=False,
        chapters=True,
        segments=[{"text": "raw", "start": 0.0}],
        agentic=True,
        fact_check=True,
        generate_images=True,
        image_style="editorial",
        image_aspect_ratio="1:1",
        image_model="gemini-image",
        image_output_dir="/tmp/images",
        article_length_words=900,
        user="kk",
        rag_mode="retrieval",
        compare_provider="OpenAI",
        compare_model="gpt-4o",
        personas=["Direct"],
    )

    assert calls[0]["kwargs"]["json"] == {
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
    assert result.raw_transcript == "raw"
    assert result.cleaned_transcript == "clean"
    assert result.chapters == [{"title": "Intro"}]
    assert result.article_draft == "draft"
    assert result.article_critique == "critique"
    assert result.fact_check_flags == [{"claim": "x", "issue": "y"}]
    assert result.generated_images == [
        {"path": "/tmp/a.png", "prompt": "p", "succeeded": True}
    ]
    assert result.article_compare == "compare"
    assert result.compare_label == "OpenAI gpt-4o"
    assert result.persona_articles == [{"name": "Direct", "text": "persona"}]
    assert result.songforge == {"lyric_draft": "lyric"}


def test_http_storage_forwards_modern_bundle_fields(monkeypatch):
    calls = []

    def fake_post(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        return FakeResponse({"url": "https://notion.so/page"})

    monkeypatch.setattr(http_adapters.requests, "post", fake_post)
    bundle = notion.ContentBundle(
        title="Title",
        transcript="transcript",
        wisdom="wisdom",
        outline="outline",
        social_content="social",
        image_prompts="prompts",
        article="article",
        summary="summary",
        tags=["tag"],
        audio_filename="audio.wav",
        models_used=["model"],
        chapters=[{"title": "Intro"}],
        article_compare="compare",
        compare_label="OpenAI gpt-4o",
        persona_articles=[{"name": "Direct", "text": "persona"}],
        article_critique="critique",
        fact_check_flags=[{"claim": "x", "issue": "y"}],
        fact_check_ran=True,
        run_metrics={"total_usd": 0.01},
        source_receipts=[{"source": "Transcript", "sha256": "abc"}],
    )

    url = http_adapters.HttpStorage().save(bundle)

    assert url == "https://notion.so/page"
    assert calls[0]["kwargs"]["json"] == {
        "title": "Title",
        "transcript": "transcript",
        "wisdom": "wisdom",
        "outline": "outline",
        "social_content": "social",
        "image_prompts": "prompts",
        "article": "article",
        "summary": "summary",
        "tags": ["tag"],
        "audio_filename": "audio.wav",
        "models_used": ["model"],
        "chapters": [{"title": "Intro"}],
        "article_compare": "compare",
        "compare_label": "OpenAI gpt-4o",
        "persona_articles": [{"name": "Direct", "text": "persona"}],
        "article_critique": "critique",
        "fact_check_flags": [{"claim": "x", "issue": "y"}],
        "fact_check_ran": True,
        "run_metrics": {"total_usd": 0.01},
        "source_receipts": [{"source": "Transcript", "sha256": "abc"}],
    }
