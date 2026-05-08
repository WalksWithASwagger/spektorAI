# WhisperForge Status

Last updated: 2026-05-08

## Current State

- Current branch: `main`
- Latest committed roadmap anchor: `c7b750a docs: add WhisperForge roadmap`
- GitHub repo: `WalksWithASwagger/spektorAI`
- Linear project: [WhisperForge Roadmap](https://linear.app/bc-ai/project/whisperforge-roadmap-317805524537)
- Primary product surface: direct Streamlit mode (`streamlit run app.py`)
- Services mode: present, but not yet at parity with the modern pipeline

## Verified

- `venv/bin/python -m pytest tests/ -q` -> `148 passed`
- `tests/smoke.sh` -> Streamlit health OK on port `8599`
- `git diff --check` -> clean before the delivery-pipeline edits

## Active Handles

- Roadmap: `ROADMAP.md`
- Delivery workflow: `docs/LINEAR-GITHUB-PIPELINE.md`
- Backlog registry: `ops/roadmap/features.json`
- GitHub issues: `#1` through `#8`
- Linear issues: `BC-57`, `BC-58`, `BC-63`, `BC-73`, `BC-83`, `BC-88`, `BC-90`, `BC-91`
- `whisperforge-env/` has been removed from the git index and remains ignored.

## Known Risks

- `tests/smoke.sh` needs permission to bind a localhost port in the Codex
  sandbox.
- GitHub CLI auth is invalid locally; use the GitHub connector or re-auth `gh`
  before relying on CLI issue/PR operations.
- Linear PR auto-linking should be verified on the first branch/PR that includes
  a `BC-*` issue key.
