# Documentation Audit - 2026-05-17

Historical note: this is the audit-time record from May 17, 2026. It is kept as
evidence of what was checked then, not as the current handoff. For current
state, use [`../STATUS.md`](../STATUS.md), [`../ROADMAP.md`](../ROADMAP.md),
and [`WHISPERFORGE-MASTER-PLAN-2026-05-18.md`](WHISPERFORGE-MASTER-PLAN-2026-05-18.md).

## Scope

This audit checked the agent-facing documentation after syncing the local
checkout with `origin`. It focused on the files a future Codex session is most
likely to trust:

- `readme.md`
- `ROADMAP.md`
- `STATUS.md`
- `changelog.md`
- `docs/LINEAR-GITHUB-PIPELINE.md`
- `ops/roadmap/features.json`
- `Makefile`
- code-adjacent comments that describe service and profile behavior

The large `patterns/` and `prompts/` markdown trees were treated as product data
and profile content, not project documentation.

## Sync Result

- `git fetch --prune origin` completed.
- Audit-time checkout: `kk/bc-83-run-recovery-foundation`, stacked on
  `kk/swarm-roadmap-batch-1` after the documentation audit and PR-review
  follow-up fixes.
- `git rev-list --left-right --count HEAD...@{u}` returned `0 0`.
- Local tracking branches were even with their upstreams:
  `main`, `kk/swarm-roadmap-batch-1`,
  `kk/bc-63-add-browser-level-streamlit-verification`, and
  `codex/agentic-delivery-contract`.

## Updates Made

- Updated `readme.md` to match the audit-time prompt profile layout, 177-test
  collection count, Ollama provider lane, Notion/markdown output shape, RAG
  environment knobs, UI ownership, and services-mode parity boundary.
- Updated `STATUS.md` with the audit-time branch/commit, sync evidence, verified
  commands, missing `gh` CLI, and services-mode parity notes.
- Updated `ROADMAP.md` so completed pieces from the first roadmap swarm batch
  are not still listed as untouched work.
- Added an `Unreleased` section to `changelog.md` for the Makefile, service
  contract tests, profile manifests, user personas, markdown source receipts,
  and this audit.

## Follow-Up Fixes

- Adjusted audio chunking/tests so WAV fixtures do not need an external
  `ffmpeg` binary; `make test` now passes locally.
- Expanded `whisperforge_core/http_adapters.py` so processing/storage HTTP
  clients forward modern pipeline options and round-trip modern result/bundle
  fields.
- Added `tests/test_http_adapters.py` to pin the HTTP adapter payloads.
- Added the credential-free `make eval-fixture` editorial/source-receipt check.
- Fixed user-defined persona selection so profile personas appear in the UI and
  resolve through the pipeline.
- Added BC-83 durable run artifacts and retry-safe history upserts.

## Verification

- `python3 -m json.tool ops/roadmap/features.json` passed.
- `git diff --check` passed after documentation edits.
- `make test` passed: 177 tests at audit time.
- `make eval-fixture` passed.
- `make smoke` passed: Streamlit health OK on port `8599`.
- `venv/bin/python tests/ui_smoke.py` passed: rendered shell OK.

## Remaining Risks

- Runtime MP3/M4A operations still need `ffmpeg` on `PATH`; the local test gate
  no longer needs it.
- Services-mode transcription still returns text-only details, so timestamped
  chapter segments are not yet available over HTTP.
- `gh` was available and authenticated during the latest swarm resume, but
  connector-backed GitHub/Linear reads remain the safer fallback if auth drifts.
