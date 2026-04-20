"""Benchmark helper: legacy "dump the whole KB" vs. RAG top-K retrieval.

Pure measurement — no LLM calls. Measures the size of the injected
knowledge-base block for each path and converts to approximate token
counts + USD at the provider's input rate. The answer tells you how
much cheaper (or more expensive) RAG is *for this specific query*,
before prompt caching even comes into play.

Why no actual LLM calls? Two reasons:

1. **Input-token size is the thing RAG changes.** Prompt caching means
   the *cost* of identical input is ~10% of list price — but you still
   pay for the tokens. RAG trims the tokens; caching trims the rate.
2. **The legacy and RAG paths produce different cache keys.** A real
   side-by-side run would spend real money on every invocation. The
   measurement here is deterministic + free, which is what a tuning
   tool should be.

Returns a compact dict the UI can render directly.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from ..cost import PRICING
from ..prompts import load_knowledge_base
from . import retriever as retriever_mod
from .chunker import Chunk
from .store import KBStore

# Same rough approximation used elsewhere — 4 chars per token is close
# enough for comparing two KB blocks of the same structure.
_CHARS_PER_TOKEN = 4


def _approx_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // _CHARS_PER_TOKEN)


def _legacy_kb_text(knowledge_base: Dict[str, str]) -> str:
    """Replicate llm._compose_kb_block's legacy path exactly."""
    if not knowledge_base:
        return ""
    kb = "\n\n".join(
        f"## {name}\n{content}" for name, content in knowledge_base.items()
    )
    return (
        "Use the following knowledge base to inform your analysis and match "
        "the user's style and perspective:\n\n"
        f"{kb}\n\n"
        "When analyzing the content, please incorporate these perspectives "
        "and style guidelines."
    )


def _input_rate_per_million(provider: str, model: str) -> float:
    """Look up the input-token rate. Returns 0 on unknown models so the
    UI still shows token counts without a misleading $ figure."""
    rates = PRICING.get((provider, model))
    return rates[0] if rates else 0.0


def compare_kb_modes(
    user: str,
    *,
    query: str,
    stage: str = "wisdom_extraction",
    provider: str = "Anthropic",
    model: str = "claude-haiku-4-5",
    k: Optional[int] = None,
) -> dict:
    """Return a comparison of legacy vs RAG for a single stage query.

    Shape of the returned dict::

        {
            "stage": str, "query_chars": int,
            "legacy": {
                "chars": int, "tokens": int, "docs": int,
                "cost_usd": float,   # per-call, un-cached
            },
            "rag": {
                "chars": int, "tokens": int, "chunks": int,
                "anchor": str | None,   # voice-anchor doc name (if any)
                "cost_usd": float,
            },
            "delta": {
                "token_savings": int,       # legacy - rag (positive = RAG cheaper)
                "token_savings_pct": float, # 0-100
                "usd_savings": float,
            },
            "provider": str, "model": str,
        }
    """
    kb = load_knowledge_base(user) or {}
    legacy_text = _legacy_kb_text(kb)
    legacy_chars = len(legacy_text)
    legacy_tokens = _approx_tokens(legacy_text)

    # RAG path — real retrieval (reads/builds the store).
    rag_kwargs = {"query": query, "stage": stage}
    if k is not None:
        rag_kwargs["k"] = k
    try:
        chunks: List[Chunk] = retriever_mod.retrieve(user, **rag_kwargs)
    except Exception:
        chunks = []
    rag_block = retriever_mod.format_block(chunks)
    rag_chars = len(rag_block)
    rag_tokens = _approx_tokens(rag_block)

    anchor_name: Optional[str] = None
    if chunks:
        first = chunks[0]
        if retriever_mod._is_voice_doc(first):
            anchor_name = first.doc_name

    in_rate = _input_rate_per_million(provider, model)
    legacy_cost = (legacy_tokens * in_rate) / 1_000_000
    rag_cost = (rag_tokens * in_rate) / 1_000_000

    delta_tokens = legacy_tokens - rag_tokens
    delta_pct = (delta_tokens / legacy_tokens * 100.0) if legacy_tokens else 0.0

    return {
        "stage": stage,
        "query_chars": len(query or ""),
        "legacy": {
            "chars": legacy_chars,
            "tokens": legacy_tokens,
            "docs": len(kb),
            "cost_usd": round(legacy_cost, 6),
        },
        "rag": {
            "chars": rag_chars,
            "tokens": rag_tokens,
            "chunks": len(chunks),
            "anchor": anchor_name,
            "cost_usd": round(rag_cost, 6),
        },
        "delta": {
            "token_savings": delta_tokens,
            "token_savings_pct": round(delta_pct, 1),
            "usd_savings": round(legacy_cost - rag_cost, 6),
        },
        "provider": provider,
        "model": model,
    }


def benchmark_all_stages(
    user: str,
    *,
    query: str,
    provider: str = "Anthropic",
    model: str = "claude-haiku-4-5",
) -> List[dict]:
    """Run ``compare_kb_modes`` across every stage with augmentation.

    Useful when you want one glance at "is RAG a win here, or are the
    stages so different that some benefit and some don't?"
    """
    return [
        compare_kb_modes(
            user, query=query, stage=stage, provider=provider, model=model,
        )
        for stage in retriever_mod.STAGE_AUGMENTATIONS
    ]
