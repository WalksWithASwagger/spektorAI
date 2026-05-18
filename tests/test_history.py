"""Tests for whisperforge_core.history — JSONL run log."""

import json

import pytest

from whisperforge_core import history


@pytest.fixture
def tmp_history(tmp_path, monkeypatch):
    f = tmp_path / "history.jsonl"
    monkeypatch.setattr(history, "HISTORY_FILE", f)
    monkeypatch.setattr(history, "CACHE_DIR", tmp_path)
    return f


def _record(title="Test", url=None, cost=0.0):
    return history.RunRecord(
        timestamp=history.now_iso(),
        title=title,
        notion_url=url,
        provider="Anthropic",
        model="claude-haiku-4-5",
        cost_usd=cost,
    )


class TestAppend:
    def test_first_append_creates_file(self, tmp_history):
        assert not tmp_history.exists()
        history.append(_record("hello"))
        assert tmp_history.exists()
        assert len(tmp_history.read_text().splitlines()) == 1

    def test_subsequent_appends_add_lines(self, tmp_history):
        for i in range(3):
            history.append(_record(f"run {i}"))
        lines = tmp_history.read_text().splitlines()
        assert len(lines) == 3
        # Each line is independently valid JSON
        for line in lines:
            data = json.loads(line)
            assert data["title"].startswith("run ")

    def test_append_survives_weird_titles(self, tmp_history):
        # Newlines + quotes in the title shouldn't break the JSONL format
        history.append(_record('weird "title" with\nnewline'))
        line = tmp_history.read_text().splitlines()[0]
        data = json.loads(line)
        assert data["title"] == 'weird "title" with\nnewline'


class TestUpsert:
    def test_without_run_id_appends(self, tmp_history):
        history.upsert(_record("one"))
        history.upsert(_record("two"))

        assert len(tmp_history.read_text().splitlines()) == 2

    def test_same_run_id_replaces_prior_record(self, tmp_history):
        first = _record("first", url="https://notion.so/old")
        first.run_id = "run-1"
        first.run_path = "/tmp/run-1"
        updated = _record("updated", url="https://notion.so/new")
        updated.run_id = "run-1"
        updated.run_path = "/tmp/run-1"
        updated.markdown_path = "/tmp/run-1/export.md"

        history.upsert(first)
        history.upsert(updated)

        lines = tmp_history.read_text().splitlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["title"] == "updated"
        assert data["notion_url"] == "https://notion.so/new"
        assert data["markdown_path"] == "/tmp/run-1/export.md"


class TestRecent:
    def test_empty_when_no_file(self, tmp_history):
        assert history.recent() == []

    def test_returns_newest_first(self, tmp_history):
        for i in range(5):
            history.append(_record(f"run {i}"))
        recent = history.recent(limit=10)
        assert [r.title for r in recent] == ["run 4", "run 3", "run 2", "run 1", "run 0"]

    def test_limit_honored(self, tmp_history):
        for i in range(20):
            history.append(_record(f"run {i}"))
        assert len(history.recent(limit=5)) == 5

    def test_malformed_lines_skipped(self, tmp_history):
        history.append(_record("valid"))
        # Inject a garbage line
        with open(tmp_history, "a") as f:
            f.write("this is not json\n")
        history.append(_record("also valid"))
        recent = history.recent()
        titles = [r.title for r in recent]
        assert "valid" in titles
        assert "also valid" in titles
        assert len(recent) == 2  # garbage line silently skipped

    def test_blank_lines_skipped(self, tmp_history):
        history.append(_record("a"))
        with open(tmp_history, "a") as f:
            f.write("\n\n   \n")
        history.append(_record("b"))
        assert len(history.recent()) == 2


class TestClear:
    def test_clear_returns_count(self, tmp_history):
        for _ in range(4):
            history.append(_record())
        assert history.clear() == 4
        assert not tmp_history.exists()
        assert history.clear() == 0  # second call is safe
