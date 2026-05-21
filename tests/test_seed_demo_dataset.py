"""Tests for the credential-free presentation demo seed pack."""

from scripts import seed_demo_dataset as demo_seed
from whisperforge_core import captures, resurfacing, run_artifacts


def test_seed_demo_dataset_creates_article_songforge_and_partial_runs(tmp_path, monkeypatch):
    monkeypatch.setattr(captures, "CAPTURES_DIR", tmp_path / "captures")
    monkeypatch.setattr(run_artifacts, "RUNS_DIR", tmp_path / "runs")

    demo_seed.main()

    capture_ids = {record.capture_id for record in captures.list_captures(limit=10)}
    assert {
        demo_seed.ARTICLE_CAPTURE_ID,
        demo_seed.SONGFORGE_CAPTURE_ID,
        demo_seed.PARTIAL_CAPTURE_ID,
    }.issubset(capture_ids)

    article_manifest = run_artifacts.load_manifest(demo_seed.ARTICLE_RUN_ID)
    assert article_manifest["status"] == "completed"
    assert _stage_names(article_manifest) == {
        "transcription", "scorecard", "session_output", "handoff_draft",
    }
    assert any(
        item["kind"] == "handoff_draft" and item["value"]
        for item in article_manifest["exports"]
    )

    songforge_output = run_artifacts.load_stage_payload(
        demo_seed.SONGFORGE_RUN_ID, "session_output"
    )
    assert "# SongForge Creative Pack" in songforge_output["article"]
    assert songforge_output["songforge"]["mode"] == "songforge"

    partial_manifest = run_artifacts.load_manifest(demo_seed.PARTIAL_RUN_ID)
    assert partial_manifest["status"] == "failed"
    assert demo_seed.PARTIAL_ERROR in partial_manifest["error"]
    assert "session_output" not in _stage_names(partial_manifest)

    default_digest = resurfacing.build_digest()
    assert default_digest["capture_filter"] == "default"
    assert all(
        "demo" not in entry["source"]
        for entries in default_digest["sections"].values()
        for entry in entries
    )

    demo_digest = resurfacing.build_digest(include_nonprod=True)
    unresolved = {entry["source"] for entry in demo_digest["sections"]["Unresolved follow-ups"]}
    strong = {entry["source"] for entry in demo_digest["sections"]["Strong outputs"]}
    assert f"run:{demo_seed.PARTIAL_RUN_ID}" in unresolved
    assert f"run:{demo_seed.ARTICLE_RUN_ID}" in strong
    assert f"run:{demo_seed.SONGFORGE_RUN_ID}" in strong


def _stage_names(manifest: dict) -> set[str]:
    return {stage.get("stage", "") for stage in manifest.get("stages", [])}
