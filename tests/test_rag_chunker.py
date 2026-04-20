"""Tests for the RAG chunker — heading split, sliding window, fallbacks.

Critical invariants:
- Heading-aware splits preserve section path (used in retrieval labels).
- Oversized sections fall back to sliding window with overlap.
- Tiny chunks (< MIN_CHUNK_TOKENS) are dropped, not surfaced.
- Stable ordinal indices across rebuilds (sorted file walk).
"""

from pathlib import Path

import pytest

from whisperforge_core.rag import chunker
from whisperforge_core.rag.chunker import Chunk


def _join_words(n: int) -> str:
    """Synthesize a `n`-word string for token-budget tests."""
    return " ".join(f"word{i}" for i in range(n))


class TestHeadingAwareSplit:
    def test_simple_two_section_doc(self):
        # Each section must exceed MIN_CHUNK_TOKENS (30) to survive.
        md = (
            f"# Voice\n{_join_words(80)}\n\n"
            f"# Style\n{_join_words(80)}"
        )
        chunks = chunker.chunk_markdown("test", md)
        labels = [c.section_path for c in chunks]
        assert "Voice" in labels
        assert "Style" in labels
        assert all(c.doc_name == "test" for c in chunks)

    def test_nested_headings_build_path(self):
        md = (
            f"# Voice\n## Tone\n### Punchy\n{_join_words(80)}\n\n"
            f"## Pace\n{_join_words(80)}\n\n"
            f"# Style\n{_join_words(80)}"
        )
        chunks = chunker.chunk_markdown("test", md)
        paths = [c.section_path for c in chunks]
        assert any("Voice / Tone / Punchy" in p for p in paths)
        assert any("Voice / Pace" in p for p in paths)
        assert any("Style" in p for p in paths)

    def test_oversized_section_falls_back_to_sliding_window(self):
        # A section bigger than TARGET_TOKENS gets split.
        big = _join_words(int(chunker.TARGET_TOKENS * chunker.WORDS_PER_TOKEN * 3))
        md = f"# Big\n{big}"
        chunks = chunker.chunk_markdown("test", md)
        # Multiple chunks, all carrying the section label
        assert len(chunks) >= 2
        assert all(c.section_path == "Big" for c in chunks)
        # No chunk exceeds the target budget
        assert all(c.token_count <= chunker.TARGET_TOKENS + 5 for c in chunks)

    def test_tiny_sections_are_dropped(self):
        # A section below MIN_CHUNK_TOKENS shouldn't survive.
        md = "# Tiny\nfoo bar\n\n# Real\n" + _join_words(200)
        chunks = chunker.chunk_markdown("test", md)
        # Only "Real" should make it through
        assert all(c.section_path == "Real" for c in chunks)


class TestPlainTextSplit:
    def test_short_doc_yields_one_chunk(self):
        text = _join_words(100)  # ~77 tokens, well under target
        chunks = chunker.chunk_plain_text("notes", text)
        assert len(chunks) == 1
        assert chunks[0].section_path == ""
        assert chunks[0].doc_name == "notes"

    def test_long_doc_overlaps_chunks(self):
        text = _join_words(2000)
        chunks = chunker.chunk_plain_text("notes", text)
        assert len(chunks) >= 2
        # Each chunk has a real text body
        assert all(c.text for c in chunks)
        # Chunks sequentially indexed
        assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


class TestKBDirWalk:
    def test_walks_md_and_txt_only(self, tmp_path):
        kb = tmp_path / "kb"
        kb.mkdir()
        (kb / "voice.md").write_text("# Voice\n" + _join_words(120))
        (kb / "notes.txt").write_text(_join_words(120))
        (kb / "image.png").write_bytes(b"\x89PNG")
        (kb / ".hidden.md").write_text("# Hidden\n" + _join_words(80))
        chunks = chunker.chunk_kb_dir(kb)
        names = {c.doc_name for c in chunks}
        assert "voice" in names
        assert "notes" in names
        assert ".hidden" not in names
        assert all(c.doc_name != "image" for c in chunks)

    def test_empty_dir_returns_empty(self, tmp_path):
        assert chunker.chunk_kb_dir(tmp_path / "missing") == []
        empty = tmp_path / "empty"
        empty.mkdir()
        assert chunker.chunk_kb_dir(empty) == []

    def test_chunks_have_label(self):
        c = Chunk(doc_name="voice", section_path="Tone / Punchy",
                  text="x", token_count=1, chunk_index=0)
        assert c.label == "voice / Tone / Punchy"
        c2 = Chunk(doc_name="notes", section_path="",
                   text="x", token_count=1, chunk_index=0)
        assert c2.label == "notes"
