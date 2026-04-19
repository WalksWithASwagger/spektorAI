"""Cost tracking for LLM + transcription calls.

Two pieces:

1. A module-level usage ledger that ``llm._call`` (and ASR callers) write
   to as they observe token counts in API responses. The ledger is a simple
   list of dicts — append-only per session, resettable by callers when they
   want per-run totals.

2. A pricing table (``PRICING``) plus ``estimate_cost()`` that converts the
   ledger into USD. Anthropic cache semantics are modelled explicitly:
   ``cache_write`` pays 1.25× input rate, ``cache_read`` pays 0.1×.

Prices are approximate (updated 2026-04 from public rate cards). Override
via ``PRICING[(provider, model)] = (input_per_million, output_per_million)``.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

# (provider, model) -> (input_$/M, output_$/M) — base rates, pre-cache.
PRICING: Dict[Tuple[str, str], Tuple[float, float]] = {
    # Anthropic Claude 4.5 line
    ("Anthropic", "claude-haiku-4-5"): (0.80, 4.00),
    ("Anthropic", "claude-sonnet-4-5"): (3.00, 15.00),
    ("Anthropic", "claude-opus-4-5"): (15.00, 75.00),
    # OpenAI 4o line
    ("OpenAI", "gpt-4o"): (2.50, 10.00),
    ("OpenAI", "gpt-4o-mini"): (0.15, 0.60),
    ("OpenAI", "gpt-4-turbo"): (10.00, 30.00),
    ("OpenAI", "gpt-4"): (30.00, 60.00),
    ("OpenAI", "gpt-3.5-turbo"): (0.50, 1.50),
    # OpenAI transcription (per-minute rates — tracked separately)
    # Whisper-1: $0.006/min; gpt-4o-transcribe: $0.006/min; mini: $0.003/min.
    # Local backends (Ollama, MLX) cost $0 by design.
}

# Per-minute rates for cloud transcription APIs.
ASR_PRICING_PER_MINUTE: Dict[str, float] = {
    "whisper-1": 0.006,
    "gpt-4o-transcribe": 0.006,
    "gpt-4o-mini-transcribe": 0.003,
}


@dataclass
class UsageRecord:
    """One LLM API call's token accounting."""
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    # Anthropic only — OpenAI caching is automatic and not exposed per-call.
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    # For ASR: billed by audio duration, not tokens.
    audio_seconds: float = 0.0


# Module-level ledger. Callers that want per-run scoping should
# snapshot(), then reset() after consuming. The Streamlit UI reads this
# directly for session-total display.
_ledger: List[UsageRecord] = []


def record(entry: UsageRecord) -> None:
    """Append one API call's usage to the session ledger."""
    _ledger.append(entry)


def ledger() -> List[UsageRecord]:
    """Return (a copy of) the current session ledger."""
    return list(_ledger)


def reset() -> None:
    """Clear the ledger. Call at the start of a run if you want per-run totals."""
    _ledger.clear()


def snapshot_and_reset() -> List[UsageRecord]:
    """Atomically capture the current ledger and clear it. Useful for
    assigning a just-completed run's usage to a history record."""
    captured = list(_ledger)
    _ledger.clear()
    return captured


@dataclass
class CostBreakdown:
    """Decomposed cost estimate suitable for showing the user."""
    total_usd: float = 0.0
    llm_usd: float = 0.0
    asr_usd: float = 0.0
    cache_savings_usd: float = 0.0  # How much we saved vs. paying full rate
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def estimate_cost(entries: Optional[List[UsageRecord]] = None) -> CostBreakdown:
    """Turn a ledger into a USD cost breakdown.

    Anthropic cache rules: reads cost 10% of input rate, writes cost 125%.
    Saved = (read_tokens * 0.9 * input_rate) + (write_tokens * -0.25 * input_rate).
    We only count positive savings in ``cache_savings_usd``.
    """
    if entries is None:
        entries = _ledger
    b = CostBreakdown(calls=len(entries))
    for u in entries:
        if u.audio_seconds:
            rate_per_min = ASR_PRICING_PER_MINUTE.get(u.model, 0.0)
            asr = (u.audio_seconds / 60.0) * rate_per_min
            b.asr_usd += asr
            b.total_usd += asr
            continue

        key = (u.provider, u.model)
        rates = PRICING.get(key)
        if not rates:
            # Unknown model — skip but count tokens so the UI can still show them.
            b.input_tokens += u.input_tokens
            b.output_tokens += u.output_tokens
            continue
        in_rate, out_rate = rates
        # Anthropic splits input tokens across three lanes; ``input_tokens``
        # in their usage object is just the non-cached portion. cache_read
        # and cache_write are separate buckets.
        regular_in = u.input_tokens
        cache_read = u.cache_read_tokens
        cache_write = u.cache_write_tokens

        cost = 0.0
        cost += (regular_in * in_rate) / 1_000_000
        cost += (cache_write * in_rate * 1.25) / 1_000_000
        cost += (cache_read * in_rate * 0.1) / 1_000_000
        cost += (u.output_tokens * out_rate) / 1_000_000

        # Hypothetical same-call cost with zero caching, for the savings stat.
        hypothetical = (
            (regular_in + cache_read + cache_write) * in_rate / 1_000_000
            + u.output_tokens * out_rate / 1_000_000
        )
        savings = hypothetical - cost
        if savings > 0:
            b.cache_savings_usd += savings

        b.llm_usd += cost
        b.total_usd += cost
        b.input_tokens += regular_in
        b.output_tokens += u.output_tokens
        b.cache_read_tokens += cache_read
        b.cache_write_tokens += cache_write

    return b
