"""Tests for durable local run artifacts."""

import json
from datetime import datetime, timezone

import pytest

from whisperforge_core import run_artifacts


@pytest.fixture
def tmp_runs_dir(tmp_path, monkeypatch):
    runs = tmp_path / "runs"
    monkeypatch.setattr(run_artifacts, "RUNS_DIR", runs)
    return runs


def test_new_run_id_has_timestamp_prefix():
    run_id = run_artifacts.new_run_id(
        datetime(2026, 5, 17, 12, 30, tzinfo=timezone.utc)
    )

    assert run_id.startswith("20260517T123000Z-")


def test_start_run_writes_manifest(tmp_runs_dir):
    path = run_artifacts.start_run("run-1", {"mode": "full_pipeline"})

    manifest = json.loads((path / "manifest.json").read_text())
    assert manifest["artifact_schema_version"] == 1
    assert manifest["run_id"] == "run-1"
    assert manifest["status"] == "running"
    assert manifest["metadata"] == {"mode": "full_pipeline"}


def test_write_stage_updates_stage_file_and_manifest(tmp_runs_dir):
    run_artifacts.start_run("run-1", {"mode": "full_pipeline"})

    stage_path = run_artifacts.write_stage(
        "run-1", "Article Draft", {"article": "draft"}
    )

    stage = json.loads(stage_path.read_text())
    manifest = run_artifacts.load_manifest("run-1")
    assert stage["payload"] == {"article": "draft"}
    assert manifest["current_stage"] == "Article Draft"
    assert manifest["stages"][0]["path"] == str(stage_path)


def test_record_export_is_idempotent_per_kind_and_value(tmp_runs_dir):
    run_artifacts.start_run("run-1", {"mode": "full_pipeline"})

    run_artifacts.record_export("run-1", "markdown", "/tmp/a.md")
    run_artifacts.record_export("run-1", "markdown", "/tmp/a.md")

    manifest = run_artifacts.load_manifest("run-1")
    assert manifest["exports"] == [
        {
            "kind": "markdown",
            "value": "/tmp/a.md",
            "updated_at": manifest["exports"][0]["updated_at"],
        }
    ]


def test_mark_status_records_failures(tmp_runs_dir):
    run_artifacts.start_run("run-1", {"mode": "full_pipeline"})

    run_artifacts.mark_status("run-1", "failed", error="boom")

    manifest = run_artifacts.load_manifest("run-1")
    assert manifest["status"] == "failed"
    assert manifest["error"] == "boom"


def test_list_manifests_summarizes_partial_runs_and_exports(tmp_runs_dir):
    run_artifacts.start_run("run-1", {
        "source": "paste",
        "recipe": {"recipe_name": "Issue handoff"},
        "settings": {"agentic": True, "images": False},
    })
    run_artifacts.record_export("run-1", "markdown", "/tmp/run.md")

    manifests = run_artifacts.list_manifests()
    summary = run_artifacts.summarize_manifest(manifests[0])

    assert summary["run_id"] == "run-1"
    assert summary["input_type"] == "paste"
    assert summary["current_stage"] == ""
    assert summary["recipe"] == "Issue handoff"
    assert summary["exports"] == "markdown"
    assert summary["settings"] == "agentic"
    assert summary["partial"] is True


def test_load_stage_payload_returns_saved_payload(tmp_runs_dir):
    run_artifacts.start_run("run-1", {"mode": "full_pipeline"})
    run_artifacts.write_stage("run-1", "session_output", {"article": "draft"})

    assert run_artifacts.load_stage_payload("run-1", "session_output") == {
        "article": "draft",
    }
    assert run_artifacts.load_stage_payload("run-1", "missing") == {}


def test_load_manifest_normalizes_legacy_artifacts(tmp_runs_dir):
    path = run_artifacts.run_dir("legacy-run")
    path.mkdir(parents=True)
    (path / "manifest.json").write_text(
        json.dumps({
            "run_id": "legacy-run",
            "created_at": "2026-05-20T00:00:00Z",
            "metadata": {"source": "paste"},
            "stages": [{"stage": "session_output", "path": "/tmp/out.json"}],
        }),
        encoding="utf-8",
    )

    manifest = run_artifacts.load_manifest("legacy-run")

    assert manifest["artifact_schema_version"] == 1
    assert manifest["status"] == "running"
    assert manifest["exports"] == []
    assert manifest["stages"] == [
        {
            "stage": "session_output",
            "path": "/tmp/out.json",
            "updated_at": "",
        }
    ]
