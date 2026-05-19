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


def test_import_capture_file_stores_text_and_source_path(tmp_captures_dir, tmp_path):
    note_path = tmp_path / "field-note.md"
    note_path.write_text("# Field note\n\nA useful observation.", encoding="utf-8")

    record = captures.import_capture_file(note_path)

    assert record is not None
    assert record.filename == "field-note.md"
    assert record.title == "# Field note"
    assert record.metadata["source_path"] == str(note_path.resolve())
    assert captures.read_capture_text(record.capture_id) == "# Field note\n\nA useful observation."


def test_import_capture_file_stores_audio_source_metadata(tmp_captures_dir, tmp_path):
    audio_path = tmp_path / "meeting.wav"
    audio_path.write_bytes(b"not real audio, just an import pointer")

    record = captures.import_capture_file(audio_path)

    assert record is not None
    assert record.filename == "meeting.wav"
    assert record.input_path is None
    assert record.metadata["import_kind"] == "audio"
    assert record.metadata["source_path"] == str(audio_path.resolve())


def test_import_capture_file_dedupes_by_source_path_and_text_hash(tmp_captures_dir, tmp_path):
    note_path = tmp_path / "note.txt"
    note_path.write_text("same idea", encoding="utf-8")
    other_note_path = tmp_path / "other-note.md"
    other_note_path.write_text("same idea", encoding="utf-8")

    first = captures.import_capture_file(note_path)
    same_path = captures.import_capture_file(note_path)
    same_text = captures.import_capture_file(other_note_path)

    assert first is not None
    assert same_path is not None
    assert same_text is not None
    assert same_path.capture_id == first.capture_id
    assert same_text.capture_id == first.capture_id
    assert len(captures.list_captures()) == 1


def test_import_capture_folder_ignores_chunks_dotfiles_and_temp_files(tmp_captures_dir, tmp_path):
    folder = tmp_path / "incoming"
    folder.mkdir()
    (folder / "keep.txt").write_text("keep me", encoding="utf-8")
    (folder / "voice.mp3").write_bytes(b"audio")
    (folder / ".hidden.md").write_text("hidden", encoding="utf-8")
    (folder / "episode_chunk_001.md").write_text("generated chunk", encoding="utf-8")
    (folder / "chunk_0.wav").write_bytes(b"generated audio chunk")
    (folder / "upload.tmp").write_text("temp", encoding="utf-8")
    (folder / "notes.txt~").write_text("backup", encoding="utf-8")

    records = captures.import_capture_folder(folder)

    assert [record.filename for record in records] == ["keep.txt", "voice.mp3"]
