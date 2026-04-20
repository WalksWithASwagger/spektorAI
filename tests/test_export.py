"""Tests for whisperforge_core.export — markdown rendering + file write."""

from datetime import datetime
from pathlib import Path

import pytest

from whisperforge_core import export, notion


def _bundle(**overrides) -> notion.ContentBundle:
    defaults = dict(
        title="A Test Run",
        transcript="Sample transcript text.",
        wisdom="Key insight.",
        outline="1. Hook. 2. Body. 3. Close.",
        social_content="Tweet: taste is leverage.",
        image_prompts="1. **Hero**: glowing workshop",
        article="# Body\n\nParagraph.",
        summary="One sentence.",
        tags=["foo", "bar"],
        audio_filename="test.mp3",
        models_used=["whisper-1", "claude-haiku-4-5"],
        chapters=[{"title": "Hook", "summary": "Intro", "start_seconds": 4.0}],
    )
    defaults.update(overrides)
    return notion.ContentBundle(**defaults)


class TestMarkdownRendering:
    def test_yaml_frontmatter_present(self):
        md = export.markdown_from_bundle(_bundle())
        assert md.startswith("---\n")
        assert "title: A Test Run" in md
        assert "source: test.mp3" in md
        # Tags render as a YAML list
        assert "tags:\n  - foo\n  - bar" in md

    def test_sections_ordered_and_present(self):
        md = export.markdown_from_bundle(_bundle())
        # Order check: chapters come before transcription
        idx_chapters = md.find("## Chapters")
        idx_transcript = md.find("## Transcription")
        idx_wisdom = md.find("## Wisdom")
        idx_article = md.find("## Article")
        assert -1 < idx_chapters < idx_transcript < idx_wisdom < idx_article

    def test_chapter_timestamp_prefix(self):
        md = export.markdown_from_bundle(_bundle(
            chapters=[
                {"title": "Start", "summary": "", "start_seconds": 0},
                {"title": "Middle", "summary": "", "start_seconds": 185},
                {"title": "End", "summary": "", "start_seconds": 3725},
            ],
        ))
        assert "[0:00] **Start**" in md
        assert "[3:05] **Middle**" in md
        assert "[1:02:05] **End**" in md

    def test_empty_sections_are_skipped(self):
        md = export.markdown_from_bundle(_bundle(outline="", wisdom=""))
        assert "## Outline" not in md
        assert "## Wisdom" not in md

    def test_fact_check_clean_when_no_flags(self):
        md = export.markdown_from_bundle(_bundle(fact_check_ran=True, fact_check_flags=[]))
        assert "## Fact check" in md
        assert "No claims flagged" in md

    def test_fact_check_flags_rendered(self):
        md = export.markdown_from_bundle(_bundle(
            fact_check_ran=True,
            fact_check_flags=[{"claim": "The sky is red", "issue": "It's blue."}],
        ))
        assert "Fact check — flags" in md
        assert "The sky is red" in md
        assert "It's blue." in md

    def test_notion_url_threads_through_frontmatter_and_metadata(self):
        md = export.markdown_from_bundle(
            _bundle(), notion_url="https://notion.so/abc123",
        )
        assert "notion_url:" in md
        assert "[https://notion.so/abc123]" in md

    def test_summary_renders_as_blockquote(self):
        md = export.markdown_from_bundle(_bundle())
        assert "> One sentence." in md


class TestExportToDisk:
    def test_creates_file_with_expected_shape(self, tmp_path):
        path = export.export(_bundle(), out_dir=tmp_path)
        assert path.exists()
        assert path.suffix == ".md"
        assert path.parent == tmp_path
        content = path.read_text()
        assert content.startswith("---")
        assert content.endswith("\n")

    def test_filename_uses_date_and_slug(self, tmp_path):
        path = export.export(_bundle(title="My Great Run!"), out_dir=tmp_path)
        today = datetime.now().strftime("%Y-%m-%d")
        assert path.name.startswith(today)
        assert "my-great-run" in path.name  # slugified

    def test_duplicate_title_same_day_disambiguates(self, tmp_path):
        p1 = export.export(_bundle(title="Same Title"), out_dir=tmp_path)
        p2 = export.export(_bundle(title="Same Title"), out_dir=tmp_path)
        assert p1 != p2
        assert p1.exists() and p2.exists()

    def test_overwrite_flag_reuses_filename(self, tmp_path):
        p1 = export.export(_bundle(title="Same"), out_dir=tmp_path)
        p2 = export.export(_bundle(title="Same"), out_dir=tmp_path, overwrite=True)
        assert p1 == p2

    def test_slugify_handles_unicode_and_punctuation(self):
        # \w matches unicode letters, so "Krüg" stays readable (ü is kept).
        assert export._slugify("Krüg's Manifesto: A/B Test!") == "krügs-manifesto-ab-test"
        assert export._slugify("") == "untitled"
        assert export._slugify("...") == "untitled"
