# WhisperForge Presentation Runbook

Date: 2026-05-19

This runbook is the shortest reliable path to show WhisperForge to collaborators.
It prioritizes what is complete now, what to avoid over-claiming, and what
feedback to request.

## 1) Credibility Check (2 minutes)

On a fresh clone, seed the credential-free demo fixture pack so the inbox and
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

- `make test` -> `281 passed`
- fixture and UI/smoke checks pass

If Docker is running and you want services proof:

```bash
make services-smoke
```

If Docker is not running, call that out explicitly and continue with direct mode.

Optional browser-level smokes (Playwright + Chromium required):

```bash
make browser-e2e        # run-history reopen + markdown export
make browser-e2e-fresh  # fresh paste -> recipe -> review -> export loop
```

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
5. Open `🧭 Review` and show the run story, source receipts, scorecard, and
   claim flags.
6. Generate an agent handoff draft, then approve-and-create a real GitHub or
   Linear issue (or append to a local follow-up queue) from the same panel.
   Dry-run is the default when target config is missing; set
   `WHISPERFORGE_HANDOFF_DRY_RUN=1` to force dry-run during a live demo.
7. Export markdown and show run artifacts.
8. Reopen the seeded `20260519T170015Z-demo0001` article/handoff run from the
   Runs dialog.
9. Generate a resurfacing digest:

```bash
venv/bin/python scripts/resurfacing_digest.py --include-all-captures
```

Seeded runs to show:

- `20260519T170015Z-demo0001`: completed article plus persisted handoff draft.
- `20260519T170415Z-demo0002`: completed SongForge source-linked creative pack.
- `20260519T170815Z-demo0003`: failed/partial run for Runs-dialog recovery
  behavior.

## 3) What To Claim vs Not Claim

Safe claims:

- Direct-mode local workbench is stable and test-backed.
- Capture -> recipe -> review -> export loop is functional.
- Run artifacts and reopen/retry flow are functional.
- Resurfacing digest and SongForge are report-only, source-linked outputs.
- Services-mode transcription forwards `text`, `segments`, and `language` over
  HTTP when the backend emits rich details (WhisperX). Non-rich backends still
  return empty segment lists by design.
- Agent handoff drafts can create real GitHub/Linear issues or append to a
  local follow-up queue from the Review tab, gated by an explicit
  "Approve and create" click. The router defaults to dry-run when target config
  is missing and honors a
  `WHISPERFORGE_HANDOFF_DRY_RUN=1` kill switch. Requires `gh` CLI authenticated
  and/or `LINEAR_API_KEY` env var for tracker writes.

Do not over-claim yet:

- Fully autonomous issue/PR acceptance checking quality.
- Resurfacing-digest auto-routing without human approval.

## 4) Reviewer Questions

Use these to get actionable feedback:

1. Which output surface is most valuable today: article, review, handoff, or digest?
2. Is the review tab trustworthy enough to publish from?
3. Should next milestone optimize for local-first use or hosted services mode?
4. For transcription priorities, rank: privacy, diarization, timestamps, cost, streaming.
5. Which routing destinations should be added next after GitHub/Linear?

## 5) Next Dev Slice (After Review)

1. Add KB governance so stale/private/canonical profile context is visible
   before generation.
2. Add fixture-backed media normalization for large audio/video routing before
   changing transcription defaults.
3. Add approved digest routing only after the local follow-up/Notion destination
   rules are clear.
