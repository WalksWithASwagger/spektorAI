"""Tests for retrieval inspection metadata."""

import hashlib
from pathlib import Path

import numpy as np
import pytest

from whisperforge_core.rag import embedder, retriever, store


def _fake_embed(texts):
    out = np.zeros((len(texts), 8), dtype=np.float32)
    for i, text in enumerate(texts):
        digest = hashlib.sha1(text.encode()).digest()[:8]
        out[i] = np.frombuffer(digest, dtype=np.uint8).astype(np.float32) / 255.0
        out[i] = out[i] / (np.linalg.norm(out[i]) + 1e-9)
    return out


@pytest.fixture(autouse=True)
def patch_env(monkeypatch, tmp_path):
    monkeypatch.setattr(embedder, "embed", _fake_embed)
    monkeypatch.setattr(embedder, "model_name", lambda: "fake-model")
    monkeypatch.setattr(embedder, "model_id_hash", lambda: "fakehash")
    from whisperforge_core import config

    monkeypatch.setattr(config, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(config, "PROMPTS_DIR", tmp_path / "prompts")
    monkeypatch.setattr(store, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(store, "PROMPTS_DIR", tmp_path / "prompts")
    return tmp_path


def _seed_kb(root: Path):
    kb = root / "prompts" / "alice" / "knowledge_base"
    kb.mkdir(parents=True)
    (kb / "voice-style.md").write_text("# Voice\n" + "voice tone style " * 220)
    (kb / "project-notes.md").write_text("# Notes\n" + "agents issues handoff " * 220)


def test_inspect_returns_roles_scores_and_excerpts(patch_env):
    _seed_kb(patch_env)

    hits = retriever.inspect(
        "alice",
        query="agent handoff from a voice capture",
        stage="wisdom_extraction",
        k=2,
    )

    assert hits
    assert hits[0].role == "voice_anchor"
    data = hits[0].to_dict()
    assert data["score"] >= -1
    assert data["stage"] == "wisdom_extraction"
    assert data["doc_name"] == "voice-style"
    assert data["excerpt"]


def test_retrieve_keeps_legacy_chunk_return_shape(patch_env):
    _seed_kb(patch_env)

    chunks = retriever.retrieve("alice", query="agent handoff", stage="social_media", k=2)

    assert chunks
    assert all(hasattr(chunk, "doc_name") for chunk in chunks)
