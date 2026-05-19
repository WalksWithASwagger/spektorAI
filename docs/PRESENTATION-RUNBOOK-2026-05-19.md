# WhisperForge Presentation Runbook

Date: 2026-05-19

This runbook is the shortest reliable path to show WhisperForge to collaborators.
It prioritizes what is complete now, what to avoid over-claiming, and what
feedback to request.

## 1) Credibility Check (2 minutes)

On a fresh clone, seed one capture and one completed run so the inbox and
Runs dialog are not empty when the demo starts:

```bash
venv/bin/python scripts/seed_demo_dataset.py
```

Then run these so the room sees real verification:

```bash
make test
make eval-fixture
venv/bin/python tests/ui_smoke.py
make smoke
```

Expected now:

- `make test` -> `246 passed`
- fixture and UI/smoke checks pass

If Docker is running and you want services proof:

```bash
make services-smoke
```

If Docker is not running, call that out explicitly and continue with direct mode.

## 2) Product Demo Flow (8-12 minutes)

Start the app:

```bash
make app
```

Then demo in this order:

1. Paste input from Wispr Flow text in the `✎ Paste` tab.
2. Save to capture inbox.
3. Pick a recipe from the command palette.
4. Run the full pipeline.
5. Open `🧭 Review` and show source receipts, scorecard, and claim flags.
6. Generate an agent handoff draft (preview only).
7. Export markdown and show run artifacts.
8. Reopen the run from the Runs dialog.
9. Generate a resurfacing digest:

```bash
make digest
```

## 3) What To Claim vs Not Claim

Safe claims:

- Direct-mode local workbench is stable and test-backed.
- Capture -> recipe -> review -> export loop is functional.
- Run artifacts and reopen/retry flow are functional.
- Resurfacing digest and SongForge are report-only, source-linked outputs.

Do not over-claim yet:

- Services-mode full parity for timestamped segment metadata.
- Fully autonomous issue/PR acceptance checking quality.
- External auto-routing from handoff/digest without human approval.

## 4) Reviewer Questions

Use these to get actionable feedback:

1. Which output surface is most valuable today: article, review, handoff, or digest?
2. Is the review tab trustworthy enough to publish from?
3. Should next milestone optimize for local-first use or hosted services mode?
4. For transcription priorities, rank: privacy, diarization, timestamps, cost, streaming.
5. Should handoff routing remain draft-only or move to approve-and-create?

## 5) Next Dev Slice (After Review)

1. Add a browser-driven end-to-end test (Playwright/localhost) for
   paste -> recipe -> review -> markdown export -> run-history reopen.
2. Close services transcription segment parity over HTTP.
3. Tighten agentic acceptance gates beyond structural checklist matching.
4. Extend the seeded demo dataset (`scripts/seed_demo_dataset.py`) to cover
   additional recipes and a partial/failed run for the Runs dialog.
