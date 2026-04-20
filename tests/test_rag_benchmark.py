"""Tests for whisperforge_core.rag.benchmark.

Measures the size-delta between legacy KB-dump and RAG top-K retrieval.
Uses the same fake embedder + tmp-path isolation pattern as test_rag_store.
"""

import hashlib
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from whisperforge_core.rag import benchmark, embedder, store


def _fake_embed(texts):
    """Same deterministic 8-dim embed as test_rag_store."""
    out = np.zeros((len(texts), 8), dtype=np.float32)
    for i, t in enumerate(texts):
        h = hashlib.sha1(t.encode()).digest()[:8]
        out[i] = np.frombuffer(h, dtype=np.uint8).astype(np.float32) / 255.0
        out[i] = out[i] / (np.linalg.norm(out[i]) + 1e-9)
    return out


@pytest.fixture(autouse=True)
def patch_env(monkeypatch, tmp_path):
    """Redirect prompts_dir + cache_dir to an isolated tmp_path so the
    benchmark can load a seeded KB and build a store without touching
    the real filesystem."""
    monkeypatch.setattr(embedder, "embed", _fake_embed)
    monkeypatch.setattr(embedder, "model_name", lambda: "fake-model")
    monkeypatch.setattr(embedder, "model_id_hash", lambda: "fakehash")
    monkeypatch.setattr(embedder, "dim", lambda: 8)
    from whisperforge_core import config, prompts
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(config, "PROMPTS_DIR", tmp_path / "prompts")
    monkeypatch.setattr(prompts, "PROMPTS_DIR", tmp_path / "prompts")
    monkeypatch.setattr(store, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(store, "PROMPTS_DIR", tmp_path / "prompts")


def _seed_kb(tmp_path: Path, user: str, files: dict) -> None:
    kb = tmp_path / "prompts" / user / "knowledge_base"
    kb.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (kb / name).write_text(content)


class TestCompareKBModes:
    def test_returns_expected_shape(self, tmp_path):
        _seed_kb(tmp_path, "alice", {
            "style-guide.md": "# Voice\n" + "voice text " * 200,
            "facts.md": "# Facts\n" + "fact text " * 200,
        })
        r = benchmark.compare_kb_modes(
            "alice", query="a query about something",
            provider="Anthropic", model="claude-haiku-4-5",
        )
        assert set(r) >= {"stage", "query_chars", "legacy", "rag",
                           "delta", "provider", "model"}
        assert set(r["legacy"]) >= {"chars", "tokens", "docs", "cost_usd"}
        assert set(r["rag"]) >= {"chars", "tokens", "chunks", "anchor",
                                  "cost_usd"}
        assert set(r["delta"]) >= {"token_savings", "token_savings_pct",
                                    "usd_savings"}

    def test_empty_kb_returns_zero_savings(self, tmp_path):
        """No KB at all → both paths return 0, delta is 0, no div-by-zero."""
        r = benchmark.compare_kb_modes("nobody", query="hi")
        assert r["legacy"]["tokens"] == 0
        assert r["rag"]["tokens"] == 0
        assert r["delta"]["token_savings"] == 0
        assert r["delta"]["token_savings_pct"] == 0.0
        assert r["delta"]["usd_savings"] == 0.0

    def test_legacy_counts_full_kb(self, tmp_path):
        _seed_kb(tmp_path, "bob", {
            "voice.md": "voice content. " * 100,
            "notes.md": "notes content. " * 100,
        })
        r = benchmark.compare_kb_modes("bob", query="test")
        # Legacy block wraps KB in a framing prelude + postscript, so the
        # char count is greater than the raw KB file sizes.
        raw = sum(len(f.read_text()) for f in
                  (tmp_path / "prompts" / "bob" / "knowledge_base").iterdir())
        assert r["legacy"]["chars"] > raw
        assert r["legacy"]["docs"] == 2
        assert r["legacy"]["tokens"] > 0

    def test_known_model_rate_produces_nonzero_cost(self, tmp_path):
        _seed_kb(tmp_path, "carol", {
            "voice.md": "v " * 5000,  # 10k chars, ~2500 tokens
        })
        r = benchmark.compare_kb_modes(
            "carol", query="q",
            provider="Anthropic", model="claude-haiku-4-5",  # $0.80/M
        )
        # 2500 tokens × $0.80 / 1M = $0.002
        assert r["legacy"]["cost_usd"] > 0
        assert r["legacy"]["cost_usd"] < 0.10  # sanity upper bound

    def test_unknown_model_cost_is_zero_but_tokens_count(self, tmp_path):
        _seed_kb(tmp_path, "dave", {"v.md": "v " * 1000})
        r = benchmark.compare_kb_modes(
            "dave", query="q",
            provider="UnknownCo", model="weird-model",
        )
        assert r["legacy"]["tokens"] > 0
        assert r["legacy"]["cost_usd"] == 0.0
        assert r["rag"]["cost_usd"] == 0.0

    def test_delta_is_legacy_minus_rag(self, tmp_path):
        _seed_kb(tmp_path, "eve", {"v.md": "voice content " * 500})
        r = benchmark.compare_kb_modes("eve", query="q")
        assert (r["delta"]["token_savings"]
                == r["legacy"]["tokens"] - r["rag"]["tokens"])


class TestBenchmarkAllStages:
    def test_returns_one_row_per_stage_with_augmentation(self, tmp_path):
        _seed_kb(tmp_path, "fred", {"v.md": "voice " * 200})
        rows = benchmark.benchmark_all_stages("fred", query="test")
        from whisperforge_core.rag.retriever import STAGE_AUGMENTATIONS
        assert len(rows) == len(STAGE_AUGMENTATIONS)
        # Stages match (order preserved from the module dict).
        stages = [r["stage"] for r in rows]
        assert stages == list(STAGE_AUGMENTATIONS.keys())
