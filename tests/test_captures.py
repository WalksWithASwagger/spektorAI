"""Tests for durable capture inbox records."""

import json
from datetime import datetime, timezone

import pytest

from whisperforge_core import captures


@pytest.fixture
def tmp_captures_dir(tmp_path, monkeypatch):
    root = tmp_path / "captures"
    monkeypatch.setattr(captures, "CAPTURES_DIR", root)
    return root


def test_new_capture_id_has_timestamp_prefix():
    capture_id = captures.new_capture_id(
        datetime(2026, 5, 18, 12, 30, tzinfo=timezone.utc)
    )

    assert capture_id.startswith("cap-20260518T123000Z-")


def test_create_text_capture_writes_record_and_input(tmp_captures_dir):
    record = captures.create_capture(
        capture_id="cap-1",
        source="Wispr Flow",
        filename="wispr.txt",
        text="Taste is leverage.\nShip the useful thing.",
    )

    data = json.loads((tmp_captures_dir / "cap-1" / "capture.json").read_text())
    assert record.source == "wispr_flow"
    assert data["text_sha256"]
    assert (tmp_captures_dir / "cap-1" / "input.txt").read_text() == (
        "Taste is leverage.\nShip the useful thing."
    )


def test_attach_run_is_idempotent_and_updates_status(tmp_captures_dir):
    captures.create_capture(capture_id="cap-1", source="paste", filename="note.txt")

    captures.attach_run("cap-1", "run-1", status="running")
    captures.attach_run("cap-1", "run-1", status="running")

    record = captures.load_capture("cap-1")
    assert record.run_ids == ["run-1"]
    assert record.status == "running"


def test_list_captures_newest_first(tmp_captures_dir):
    captures.create_capture(capture_id="cap-old", source="paste", filename="old.txt")
    captures.create_capture(capture_id="cap-new", source="paste", filename="new.txt")
    captures.mark_status("cap-new", "completed")

    records = captures.list_captures()

    assert [r.capture_id for r in records] == ["cap-new", "cap-old"]


def test_run_metadata_is_compact(tmp_captures_dir):
    captures.create_capture(
        capture_id="cap-1",
        source="paste",
        filename="note.txt",
        title="A note",
        text="hello world",
    )

    metadata = captures.run_metadata("cap-1")

    assert metadata["capture_id"] == "cap-1"
    assert metadata["source"] == "paste"
    assert metadata["text_excerpt"] == "hello world"
