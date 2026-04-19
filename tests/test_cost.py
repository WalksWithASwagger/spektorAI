"""Tests for whisperforge_core.cost — usage ledger + cost estimation.

Cache pricing math is the tricky bit: Anthropic charges 1.25× input rate
for cache_write tokens and 0.1× for cache_read tokens. The tests pin this
so a future refactor can't silently drift.
"""

import pytest

from whisperforge_core import cost


@pytest.fixture(autouse=True)
def clean_ledger():
    """Each test gets a fresh empty ledger."""
    cost.reset()
    yield
    cost.reset()


class TestLedger:
    def test_empty_ledger_zero_cost(self):
        b = cost.estimate_cost()
        assert b.total_usd == 0
        assert b.calls == 0

    def test_record_and_readback(self):
        cost.record(cost.UsageRecord(
            provider="Anthropic", model="claude-haiku-4-5",
            input_tokens=100, output_tokens=50,
        ))
        b = cost.estimate_cost()
        assert b.calls == 1
        assert b.input_tokens == 100
        assert b.output_tokens == 50

    def test_reset_clears(self):
        cost.record(cost.UsageRecord(provider="OpenAI", model="gpt-4o"))
        assert cost.estimate_cost().calls == 1
        cost.reset()
        assert cost.estimate_cost().calls == 0

    def test_snapshot_and_reset_atomic(self):
        cost.record(cost.UsageRecord(provider="OpenAI", model="gpt-4o-mini",
                                     input_tokens=10, output_tokens=5))
        snap = cost.snapshot_and_reset()
        assert len(snap) == 1
        assert cost.estimate_cost().calls == 0


class TestCachePricing:
    """Anthropic cache math: reads 0.1×, writes 1.25× of input rate."""

    def test_no_cache_charges_full_input(self):
        cost.record(cost.UsageRecord(
            provider="Anthropic", model="claude-haiku-4-5",
            input_tokens=1_000_000, output_tokens=0,
        ))
        b = cost.estimate_cost()
        # Haiku 4.5 input = $0.80/M → exactly $0.80
        assert b.total_usd == pytest.approx(0.80, abs=1e-6)
        assert b.cache_savings_usd == 0

    def test_cache_read_pays_10_percent(self):
        cost.record(cost.UsageRecord(
            provider="Anthropic", model="claude-haiku-4-5",
            input_tokens=0, output_tokens=0,
            cache_read_tokens=1_000_000, cache_write_tokens=0,
        ))
        b = cost.estimate_cost()
        assert b.total_usd == pytest.approx(0.08, abs=1e-6)      # 10% of $0.80
        # Saved $0.80 - $0.08 = $0.72 vs. paying full rate
        assert b.cache_savings_usd == pytest.approx(0.72, abs=1e-6)

    def test_cache_write_costs_125_percent(self):
        cost.record(cost.UsageRecord(
            provider="Anthropic", model="claude-haiku-4-5",
            input_tokens=0, output_tokens=0,
            cache_read_tokens=0, cache_write_tokens=1_000_000,
        ))
        b = cost.estimate_cost()
        assert b.total_usd == pytest.approx(1.00, abs=1e-6)      # 125% of $0.80
        # Write is MORE expensive than full rate, so it's not a "saving"
        assert b.cache_savings_usd == 0

    def test_mixed_pipeline_pattern(self):
        """5-stage pipeline: 1 write + 4 reads of the same KB prefix.
        Proves the savings calc matches what we've been claiming live."""
        # Stage 1: KB lands in cache. 100 regular input + 5000 cache_write
        cost.record(cost.UsageRecord(
            provider="Anthropic", model="claude-haiku-4-5",
            input_tokens=100, output_tokens=500,
            cache_read_tokens=0, cache_write_tokens=5000,
        ))
        # Stages 2-5: 4× cache_read on same KB
        for _ in range(4):
            cost.record(cost.UsageRecord(
                provider="Anthropic", model="claude-haiku-4-5",
                input_tokens=200, output_tokens=500,
                cache_read_tokens=5000, cache_write_tokens=0,
            ))
        b = cost.estimate_cost()
        assert b.cache_read_tokens == 20_000
        assert b.cache_write_tokens == 5_000
        assert b.cache_savings_usd > 0  # 4 reads saved real money
        assert b.calls == 5


class TestModelRouting:
    def test_openai_pricing_applied(self):
        cost.record(cost.UsageRecord(
            provider="OpenAI", model="gpt-4o-mini",
            input_tokens=1_000_000, output_tokens=1_000_000,
        ))
        b = cost.estimate_cost()
        # gpt-4o-mini: $0.15/M in + $0.60/M out = $0.75
        assert b.total_usd == pytest.approx(0.75, abs=1e-6)

    def test_unknown_model_is_free_not_error(self):
        cost.record(cost.UsageRecord(
            provider="SomeFuture", model="made-up-0.1",
            input_tokens=1000, output_tokens=1000,
        ))
        b = cost.estimate_cost()
        # Unknown provider: cost is $0 but tokens still counted
        assert b.total_usd == 0
        assert b.input_tokens == 1000

    def test_ollama_local_is_free(self):
        cost.record(cost.UsageRecord(
            provider="Ollama (local)", model="llama3:latest",
            input_tokens=50_000, output_tokens=10_000,
        ))
        b = cost.estimate_cost()
        assert b.total_usd == 0
        assert b.llm_usd == 0


class TestASRPricing:
    def test_whisper_per_minute_billing(self):
        cost.record(cost.UsageRecord(
            provider="OpenAI", model="whisper-1",
            audio_seconds=120.0,
        ))
        b = cost.estimate_cost()
        # 2 minutes × $0.006/min = $0.012
        assert b.total_usd == pytest.approx(0.012, abs=1e-6)
        assert b.asr_usd == pytest.approx(0.012, abs=1e-6)

    def test_mini_transcribe_half_price(self):
        cost.record(cost.UsageRecord(
            provider="OpenAI", model="gpt-4o-mini-transcribe",
            audio_seconds=60.0,
        ))
        b = cost.estimate_cost()
        assert b.total_usd == pytest.approx(0.003, abs=1e-6)
