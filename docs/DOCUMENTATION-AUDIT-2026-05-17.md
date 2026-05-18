# Documentation Audit - 2026-05-17

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
- Current checkout: `kk/swarm-roadmap-batch-1` at
  `26c9ecb feat: ship first roadmap swarm batch`.
- `git rev-list --left-right --count HEAD...@{u}` returned `0 0`.
- Local tracking branches were even with their upstreams:
  `main`, `kk/swarm-roadmap-batch-1`,
  `kk/bc-63-add-browser-level-streamlit-verification`, and
  `codex/agentic-delivery-contract`.

## Updates Made

- Updated `readme.md` to match the current prompt profile layout, 166-test
  collection count, Ollama provider lane, Notion/markdown output shape, RAG
  environment knobs, UI ownership, and services-mode parity boundary.
- Updated `STATUS.md` with the current branch/commit, sync evidence, verified
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

## Verification

- `python3 -m json.tool ops/roadmap/features.json` passed.
- `git diff --check` passed after documentation edits.
- `make test` passed: 166 tests.
- `make smoke` passed: Streamlit health OK on port `8599`.
- `venv/bin/python tests/ui_smoke.py` passed: rendered shell OK.

## Remaining Risks

- Runtime MP3/M4A operations still need `ffmpeg` on `PATH`; the local test gate
  no longer needs it.
- Services-mode transcription still returns text-only details, so timestamped
  chapter segments are not yet available over HTTP.
- `gh` is not installed in this environment, so GitHub and Linear issue/PR
  state was not refreshed from the CLI. Use the GitHub/Linear connectors or
  install/authenticate `gh` before updating external tracker status.
