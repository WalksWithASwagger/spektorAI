"""Credential-free editorial fixture check for source receipts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "editorial_eval.json"
SONGFORGE_FIXTURE = ROOT / "tests" / "fixtures" / "songforge_eval.json"

sys.path.insert(0, str(ROOT))

from whisperforge_core import export, notion, scorecards, songforge


def _load_fixture(path: Path = FIXTURE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run(path: Path = FIXTURE) -> None:
    fixture = _load_fixture(path)
    bundle = notion.ContentBundle(
        title=fixture["title"],
        transcript=fixture["transcript"],
        article=fixture["article"],
        summary=fixture["summary"],
        tags=fixture["tags"],
        fact_check_ran=True,
        fact_check_flags=fixture["fact_check_flags"],
        run_metrics={
            "backend": "fixture",
            "source_receipts": fixture["source_receipts"],
            "scorecard": scorecards.build_summary(
                article=fixture["article"],
                transcript=fixture["transcript"],
                source_receipts=fixture["source_receipts"],
                fact_check_flags=fixture["fact_check_flags"],
                fact_check_ran=True,
                recipe_effective_settings={
                    "output_sections": ["article", "source_receipts"],
                    "eval_checks": ["source_receipts", "fact_check_flags"],
                    "handoff_targets": ["markdown"],
                },
            ),
        },
    )
    markdown = export.markdown_from_bundle(bundle)

    for expected in fixture["expected_markdown"]:
        if expected not in markdown:
            raise AssertionError(f"missing expected markdown: {expected!r}")

    print(
        "editorial-eval: "
        f"{len(fixture['source_receipts'])} receipt(s), "
        f"{len(fixture['fact_check_flags'])} fact-check flag(s), "
        "scorecard rendered"
    )
    run_songforge_eval()


def run_songforge_eval(path: Path = SONGFORGE_FIXTURE) -> None:
    fixture = _load_fixture(path)
    pack = songforge.build_pack(
        fixture["transcript"],
        fixture.get("knowledge_base") or {},
    )
    if sorted(pack) != fixture["expected_pack_keys"]:
        raise AssertionError("SongForge pack keys do not match fixture")
    variant_names = [variant["name"] for variant in pack["structure_variants"]]
    if variant_names != fixture["expected_structure_variants"]:
        raise AssertionError("SongForge structure variants do not match fixture")
    if pack["originality_guardrails"] != fixture["expected_originality_guardrails"]:
        raise AssertionError("SongForge originality guardrails do not match fixture")
    markdown = songforge.render_markdown(pack)
    for expected in fixture["expected_markdown"]:
        if expected not in markdown:
            raise AssertionError(f"missing expected SongForge markdown: {expected!r}")
    print("songforge-eval: structure variants, guardrails, prompt pack, and source notes rendered")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"editorial-eval failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
