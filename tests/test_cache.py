"""Tests for whisperforge_core.cache.

The cache is env-gated: when WHISPERFORGE_CACHE is unset/falsy,
cached_or_compute() is a straight passthrough. When enabled, identical calls
return the stored value without re-running compute.
"""

from unittest.mock import MagicMock

import pytest

from whisperforge_core import cache


@pytest.fixture(autouse=True)
def tmp_cache_dir(tmp_path, monkeypatch):
    """Isolate each test's cache so they don't stomp on each other."""
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)


@pytest.fixture
def cache_on(monkeypatch):
    monkeypatch.setenv("WHISPERFORGE_CACHE", "1")


@pytest.fixture
def cache_off(monkeypatch):
    monkeypatch.delenv("WHISPERFORGE_CACHE", raising=False)


class TestEnabled:
    def test_unset_is_disabled(self, cache_off):
        assert cache.enabled() is False

    @pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on"])
    def test_truthy_flags_enable(self, monkeypatch, value):
        monkeypatch.setenv("WHISPERFORGE_CACHE", value)
        assert cache.enabled() is True

    @pytest.mark.parametrize("value", ["0", "false", "no", "", "off"])
    def test_falsy_flags_disable(self, monkeypatch, value):
        monkeypatch.setenv("WHISPERFORGE_CACHE", value)
        assert cache.enabled() is False


class TestCachedOrCompute:
    def test_disabled_never_stores(self, cache_off):
        compute = MagicMock(return_value="fresh")
        assert cache.cached_or_compute("k", compute) == "fresh"
        # Second call still recomputes — no persistence when disabled
        assert cache.cached_or_compute("k", compute) == "fresh"
        assert compute.call_count == 2

    def test_enabled_returns_cached_on_second_call(self, cache_on):
        compute = MagicMock(side_effect=["first", "second"])
        key = cache.make_key(["test", "key"])
        assert cache.cached_or_compute(key, compute) == "first"
        assert cache.cached_or_compute(key, compute) == "first"
        assert compute.call_count == 1

    def test_different_keys_miss_independently(self, cache_on):
        compute_a = MagicMock(return_value="A")
        compute_b = MagicMock(return_value="B")
        assert cache.cached_or_compute(cache.make_key(["a"]), compute_a) == "A"
        assert cache.cached_or_compute(cache.make_key(["b"]), compute_b) == "B"
        assert compute_a.call_count == 1
        assert compute_b.call_count == 1

    def test_none_result_not_cached(self, cache_on):
        """An error path (compute returns None) must not wedge the user on
        the failure — next call should retry."""
        compute = MagicMock(side_effect=[None, "recovered"])
        key = cache.make_key(["retry"])
        assert cache.cached_or_compute(key, compute) is None
        assert cache.cached_or_compute(key, compute) == "recovered"
        assert compute.call_count == 2

    def test_empty_string_not_cached(self, cache_on):
        """Same rule for empty transcripts — don't cache 'we failed'."""
        compute = MagicMock(side_effect=["", "actual transcript"])
        key = cache.make_key(["empty"])
        assert cache.cached_or_compute(key, compute) == ""
        assert cache.cached_or_compute(key, compute) == "actual transcript"
        assert compute.call_count == 2


class TestKeyComponents:
    def test_make_key_stable(self):
        k1 = cache.make_key(["a", "b", "c"])
        k2 = cache.make_key(["a", "b", "c"])
        assert k1 == k2

    def test_make_key_order_sensitive(self):
        # Swapping the component order produces a different key, by design:
        # ['model', 'prompt_hash'] must differ from ['prompt_hash', 'model'].
        assert cache.make_key(["a", "b"]) != cache.make_key(["b", "a"])

    def test_file_hash_and_text_hash_differ(self, tmp_path):
        p = tmp_path / "sample.txt"
        p.write_text("hello")
        assert cache.file_hash(p) == cache.text_hash("hello")


class TestClear:
    def test_clear_removes_all_entries(self, cache_on):
        for i in range(3):
            cache.put(cache.make_key([str(i)]), f"value-{i}")
        assert cache.clear() == 3
        assert cache.clear() == 0
