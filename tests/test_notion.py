"""Tests for whisperforge_core.notion — block chunker and ContentBundle layout.

The 1900-char chunker is load-bearing: Notion rejects >2000-char rich_text
blocks. These tests pin that behavior so nobody quietly loosens it.
"""

import pytest

from whisperforge_core import notion


class TestChunkTextForNotion:
    def test_empty_string_returns_empty_list(self):
        assert notion.chunk_text_for_notion("") == []

    def test_short_text_single_chunk(self):
        assert notion.chunk_text_for_notion("hello world") == ["hello world"]

    def test_exactly_1900_chars_single_chunk(self):
        text = "a" * 1900
        chunks = notion.chunk_text_for_notion(text)
        assert len(chunks) == 1
        assert len(chunks[0]) == 1900

    def test_1901_chars_splits_into_two(self):
        text = "a" * 1901
        chunks = notion.chunk_text_for_notion(text)
        assert len(chunks) == 2
        assert len(chunks[0]) == 1900
        assert len(chunks[1]) == 1

    def test_10000_chars_splits_into_six_chunks(self):
        text = "b" * 10_000
        chunks = notion.chunk_text_for_notion(text)
        # ceil(10000/1900) == 6
        assert len(chunks) == 6
        assert sum(len(c) for c in chunks) == 10_000
        assert all(len(c) <= 1900 for c in chunks)

    def test_unicode_preserved(self):
        text = "café " * 500  # ~2500 chars
        chunks = notion.chunk_text_for_notion(text)
        assert "".join(chunks) == text
        # Notion counts chars, so unicode bytes aren't relevant
        assert all(len(c) <= 1900 for c in chunks)

    def test_no_block_exceeds_notion_limit(self):
        """Guard against any future chunk_size regression above 2000."""
        text = "x" * 50_000
        chunks = notion.chunk_text_for_notion(text)
        assert all(len(c) < 2000 for c in chunks), "Notion would reject a block >=2000 chars"


class TestContentBundleBlocks:
    def test_minimal_bundle_builds_metadata_only(self):
        bundle = notion.ContentBundle(title="Test")
        blocks = notion.build_blocks(bundle)
        # At minimum: divider + heading + 4 metadata paragraphs
        assert any(b["type"] == "heading_2" for b in blocks)
        paragraphs = [b for b in blocks if b["type"] == "paragraph"]
        assert len(paragraphs) >= 4  # filename, created, models, tokens

    def test_full_bundle_includes_every_section(self):
        bundle = notion.ContentBundle(
            title="Full",
            transcript="T" * 100,
            wisdom="W" * 100,
            outline="O" * 100,
            social_content="S" * 100,
            image_prompts="I" * 100,
            article="A" * 100,
            summary="brief summary",
            tags=["a", "b"],
            audio_filename="file.m4a",
            models_used=["OpenAI gpt-4", "OpenAI Whisper-1"],
        )
        blocks = notion.build_blocks(bundle)
        toggle_labels = [
            b["toggle"]["rich_text"][0]["text"]["content"]
            for b in blocks if b["type"] == "toggle"
        ]
        assert "Transcription" in toggle_labels
        assert "Wisdom" in toggle_labels
        assert "Socials" in toggle_labels
        assert "Image Prompts" in toggle_labels
        assert "Outline" in toggle_labels
        assert "Draft Post" in toggle_labels
        assert "Original Audio" in toggle_labels

    def test_long_transcript_uses_chunked_paragraphs(self):
        bundle = notion.ContentBundle(title="Long", transcript="z" * 5000)
        blocks = notion.build_blocks(bundle)
        transcription_toggles = [
            b for b in blocks
            if b["type"] == "toggle"
            and b["toggle"]["rich_text"][0]["text"]["content"] == "Transcription"
        ]
        assert len(transcription_toggles) == 1
        paragraphs = transcription_toggles[0]["toggle"]["children"]
        # 5000 / 1900 = 3 chunks
        assert len(paragraphs) == 3
        for p in paragraphs:
            assert len(p["paragraph"]["rich_text"][0]["text"]["content"]) <= 1900


class TestChaptersBlock:
    """The Chapters toggle appears near the top (above Transcription) and
    renders each chapter as a bulleted list item with optional [MM:SS] prefix."""

    def test_no_chapters_no_block(self):
        bundle = notion.ContentBundle(title="t", transcript="body")
        blocks = notion.build_blocks(bundle)
        assert not any(
            b["type"] == "toggle"
            and b["toggle"]["rich_text"][0]["text"]["content"] == "Chapters"
            for b in blocks
        )

    def test_chapters_render_as_bulleted_children(self):
        bundle = notion.ContentBundle(
            title="t",
            chapters=[
                {"title": "Opening", "summary": "Intro remarks.", "start_quote": "Welcome..."},
                {"title": "Main Point", "summary": "The core argument.", "start_quote": "So..."},
            ],
        )
        blocks = notion.build_blocks(bundle)
        chapters = [b for b in blocks if b["type"] == "toggle"
                    and b["toggle"]["rich_text"][0]["text"]["content"] == "Chapters"]
        assert len(chapters) == 1
        bullets = chapters[0]["toggle"]["children"]
        assert len(bullets) == 2
        assert all(b["type"] == "bulleted_list_item" for b in bullets)
        first = bullets[0]["bulleted_list_item"]["rich_text"][0]["text"]["content"]
        assert "Opening" in first and "Intro remarks" in first

    def test_timestamped_chapters_get_mmss_prefix(self):
        bundle = notion.ContentBundle(
            title="t",
            chapters=[
                {"title": "Start", "summary": "", "start_seconds": 0},
                {"title": "Middle", "summary": "", "start_seconds": 185},  # 3:05
                {"title": "End", "summary": "", "start_seconds": 3725},     # 1:02:05
            ],
        )
        blocks = notion.build_blocks(bundle)
        bullets = next(b for b in blocks if b["type"] == "toggle"
                       and b["toggle"]["rich_text"][0]["text"]["content"] == "Chapters")["toggle"]["children"]
        texts = [b["bulleted_list_item"]["rich_text"][0]["text"]["content"] for b in bullets]
        assert "[0:00]" in texts[0]
        assert "[3:05]" in texts[1]
        assert "[1:02:05]" in texts[2]

    def test_chapters_appear_above_transcription(self):
        bundle = notion.ContentBundle(
            title="t",
            transcript="body",
            chapters=[{"title": "Opening", "summary": "x", "start_quote": "y"}],
        )
        blocks = notion.build_blocks(bundle)
        labels = [
            b["toggle"]["rich_text"][0]["text"]["content"]
            for b in blocks if b["type"] == "toggle"
        ]
        assert labels.index("Chapters") < labels.index("Transcription")


class TestEstimateTokens:
    def test_empty_bundle_has_overhead(self):
        tokens = notion.estimate_tokens(notion.ContentBundle(title=""))
        assert tokens == 1000  # 0 content + 1000 overhead

    def test_token_count_scales_with_content(self):
        short = notion.estimate_tokens(notion.ContentBundle(title="", transcript="a" * 40))
        long = notion.estimate_tokens(notion.ContentBundle(title="", transcript="a" * 4000))
        assert long > short
        # 4000 chars @ 4 chars/token = 1000 tokens, plus 1000 overhead
        assert 1900 <= long <= 2100


class TestRunMetricsBlock:
    """Run metrics toggle carries the cost/token/duration/flags receipt."""

    def _toggles(self, bundle):
        return [
            b for b in notion.build_blocks(bundle)
            if b["type"] == "toggle"
        ]

    def _toggle_labels(self, bundle):
        return [
            b["toggle"]["rich_text"][0]["text"]["content"]
            for b in self._toggles(bundle)
        ]

    def test_no_metrics_no_block(self):
        bundle = notion.ContentBundle(title="no-metrics")
        assert "Run metrics" not in self._toggle_labels(bundle)

    def test_metrics_present_renders_toggle(self):
        bundle = notion.ContentBundle(
            title="with-metrics",
            run_metrics={
                "total_usd": 0.0123,
                "llm_usd": 0.0100,
                "asr_usd": 0.0023,
                "cache_savings_usd": 0.0051,
                "calls": 7,
                "input_tokens": 1200,
                "output_tokens": 800,
                "cache_read_tokens": 5000,
                "cache_write_tokens": 600,
                "duration_seconds": 34.5,
                "backend": "openai",
                "flags": {"agentic": True, "fact_check": False,
                          "chapters": True, "images": False},
            },
        )
        labels = self._toggle_labels(bundle)
        assert "Run metrics" in labels
        # Extract the rendered text of the Run metrics toggle.
        metrics = next(
            b for b in self._toggles(bundle)
            if b["toggle"]["rich_text"][0]["text"]["content"] == "Run metrics"
        )
        body = "\n".join(
            p["paragraph"]["rich_text"][0]["text"]["content"]
            for p in metrics["toggle"]["children"]
        )
        assert "$0.0123" in body      # total
        assert "$0.0051" in body      # cache savings
        assert "34s" in body          # duration under a minute
        assert "openai" in body       # backend
        assert "agentic" in body      # only enabled flags listed
        assert "fact_check" not in body
        assert "1,200" in body        # input tokens with comma
        assert "5,000" in body        # cache read
        assert "7" in body            # calls

    def test_duration_over_minute_formats_mm_ss(self):
        bundle = notion.ContentBundle(
            title="long",
            run_metrics={"duration_seconds": 134.0, "calls": 1},
        )
        metrics = next(
            b for b in notion.build_blocks(bundle)
            if b["type"] == "toggle"
            and b["toggle"]["rich_text"][0]["text"]["content"] == "Run metrics"
        )
        body = "\n".join(
            p["paragraph"]["rich_text"][0]["text"]["content"]
            for p in metrics["toggle"]["children"]
        )
        assert "2m 14s" in body

    def test_no_flags_enabled_shows_none(self):
        bundle = notion.ContentBundle(
            title="bare",
            run_metrics={"flags": {"agentic": False, "images": False}},
        )
        metrics = next(
            b for b in notion.build_blocks(bundle)
            if b["type"] == "toggle"
            and b["toggle"]["rich_text"][0]["text"]["content"] == "Run metrics"
        )
        body = "\n".join(
            p["paragraph"]["rich_text"][0]["text"]["content"]
            for p in metrics["toggle"]["children"]
        )
        assert "Flags on:** none" in body

    def test_metrics_appears_before_metadata_heading(self):
        """Receipt should sit above the Metadata heading, not after."""
        bundle = notion.ContentBundle(
            title="order",
            run_metrics={"total_usd": 0.01, "calls": 1},
        )
        blocks = notion.build_blocks(bundle)
        # Find indices.
        metrics_idx = next(
            i for i, b in enumerate(blocks)
            if b["type"] == "toggle"
            and b["toggle"]["rich_text"][0]["text"]["content"] == "Run metrics"
        )
        heading_idx = next(
            i for i, b in enumerate(blocks) if b["type"] == "heading_2"
        )
        assert metrics_idx < heading_idx
