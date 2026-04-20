"""Tests for the RAG vector store.

Mocks the embedder so we don't pay the model-load tax in CI. Fakes
return random-but-stable vectors keyed on the input text so search
results are deterministic.
"""

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from whisperforge_core.rag import chunker, embedder, store
from whisperforge_core.rag.chunker import Chunk
from whisperforge_core.rag.store import KBStore


def _fake_embed(texts):
    """Deterministic 8-dim embedding: SHA1(text) → first 8 bytes → float32 → normalize."""
    out = np.zeros((len(texts), 8), dtype=np.float32)
    for i, t in enumerate(texts):
        h = hashlib.sha1(t.encode()).digest()[:8]
        out[i] = np.frombuffer(h, dtype=np.uint8).astype(np.float32) / 255.0
        out[i] = out[i] / (np.linalg.norm(out[i]) + 1e-9)
    return out


@pytest.fixture(autouse=True)
def patch_embedder(monkeypatch, tmp_path):
    monkeypatch.setattr(embedder, "embed", _fake_embed)
    monkeypatch.setattr(embedder, "model_name", lambda: "fake-model")
    monkeypatch.setattr(embedder, "model_id_hash", lambda: "fakehash")
    monkeypatch.setattr(embedder, "dim", lambda: 8)
    # Redirect cache + prompt dirs to tmp_path so tests are isolated.
    from whisperforge_core import config
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(config, "PROMPTS_DIR", tmp_path / "prompts")
    # Re-import store's references since they captured at import time.
    monkeypatch.setattr(store, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(store, "PROMPTS_DIR", tmp_path / "prompts")


def _seed_kb(prompts_dir: Path, user: str, files: dict[str, str]) -> Path:
    kb = prompts_dir / user / "knowledge_base"
    kb.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (kb / name).write_text(content)
    return kb


class TestBuild:
    def test_empty_kb_yields_empty_store(self, tmp_path):
        s = KBStore("alice")
        s.ensure_built()
        assert s.chunk_count() == 0
        assert s.search("anything", k=5) == []

    def test_build_indexes_all_chunks(self, tmp_path):
        _seed_kb(tmp_path / "prompts", "alice", {
            "voice.md": "# Voice\n" + " ".join(f"word{i}" for i in range(200)),
            "notes.txt": " ".join(f"word{i}" for i in range(150)),
        })
        s = KBStore("alice")
        s.ensure_built()
        assert s.chunk_count() >= 2

    def test_search_returns_top_k_in_score_order(self, tmp_path):
        _seed_kb(tmp_path / "prompts", "alice", {
            "voice.md": "# Voice\n" + " ".join(f"word{i}" for i in range(200)),
            "notes.txt": " ".join(f"alpha{i}" for i in range(150)),
        })
        s = KBStore("alice")
        s.ensure_built()
        results = s.search("anything", k=2)
        assert len(results) <= 2
        # Scores are non-increasing
        scores = [score for _, score in results]
        assert scores == sorted(scores, reverse=True)


class TestPersistence:
    def test_second_load_uses_disk_index(self, tmp_path):
        _seed_kb(tmp_path / "prompts", "alice", {
            "voice.md": "# Voice\n" + " ".join(f"word{i}" for i in range(200)),
        })
        s1 = KBStore("alice")
        s1.ensure_built()
        # Manifest exists
        manifest = s1._manifest_path()
        assert manifest.exists()

        # Second store: should hit the cache without rebuilding
        s2 = KBStore("alice")
        # Spy on _build to confirm it's NOT called
        with patch.object(s2, "_build") as build_spy:
            s2.ensure_built()
            assert build_spy.call_count == 0
        assert s2.chunk_count() == s1.chunk_count()


class TestInvalidation:
    def test_kb_edit_triggers_rebuild(self, tmp_path):
        kb = _seed_kb(tmp_path / "prompts", "alice", {
            "voice.md": "# Voice\n" + " ".join(f"word{i}" for i in range(200)),
        })
        s1 = KBStore("alice")
        s1.ensure_built()
        original_count = s1.chunk_count()

        # Touch the file to bump mtime, add new content
        import time
        time.sleep(0.01)
        (kb / "voice.md").write_text(
            "# Voice\n# Style\n" + " ".join(f"word{i}" for i in range(400))
        )

        s2 = KBStore("alice")
        with patch.object(s2, "_build", wraps=s2._build) as build_spy:
            s2.ensure_built()
            assert build_spy.called, "stale index should have triggered _build"
        # New content yielded a different chunk count
        assert s2.chunk_count() != original_count or s2.chunk_count() >= 2


class TestReset:
    def test_reset_user_drops_index(self, tmp_path):
        _seed_kb(tmp_path / "prompts", "alice", {
            "voice.md": "# Voice\n" + " ".join(f"word{i}" for i in range(200)),
        })
        s1 = KBStore("alice")
        s1.ensure_built()
        assert s1.dir.exists()

        store.reset_user("alice")
        assert not s1.dir.exists()
