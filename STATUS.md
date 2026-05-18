# WhisperForge Status

Last updated: 2026-05-18

## Current State

- Active branch for the product reset: `codex/whisperforge-master-plan-2026-05-18`.
- Baseline before this branch: `main` at `e607252 feat: add agentic delivery contract`,
  synced with `origin/main`.
- GitHub repo: `WalksWithASwagger/spektorAI`.
- Linear project: [WhisperForge Roadmap](https://linear.app/bc-ai/project/whisperforge-roadmap-317805524537).
- Primary product surface: direct Streamlit mode (`make app`).
- Services mode: present through `docker compose`; direct mode remains the
  product lead unless service parity is the explicit issue scope.
- Latest strategy anchor:
  [`docs/WHISPERFORGE-MASTER-PLAN-2026-05-18.md`](docs/WHISPERFORGE-MASTER-PLAN-2026-05-18.md).

## Verified Baseline

- `git status --short --branch` -> clean `main` before branch creation.
- `git rev-list --left-right --count HEAD...@{u}` -> `0 0`.
- GitHub open issues before the new wave: none.
- GitHub open PRs before the new wave: none.
- Linear issues `BC-57`, `BC-58`, `BC-63`, `BC-73`, `BC-83`, `BC-88`,
  `BC-90`, and `BC-91` were all `Done`.
- Previous post-merge verification passed:
  - `make test` -> `192 passed`
  - `make eval-fixture`
  - `make smoke`
  - `venv/bin/python tests/ui_smoke.py`
  - `python3 -m json.tool ops/roadmap/features.json`
  - `git diff --check`

## Active Handles

- Roadmap: [`ROADMAP.md`](ROADMAP.md)
- Master plan: [`docs/WHISPERFORGE-MASTER-PLAN-2026-05-18.md`](docs/WHISPERFORGE-MASTER-PLAN-2026-05-18.md)
- Delivery workflow: [`docs/LINEAR-GITHUB-PIPELINE.md`](docs/LINEAR-GITHUB-PIPELINE.md)
- Backlog registry: [`ops/roadmap/features.json`](ops/roadmap/features.json)
- Agentic contract: [`docs/AGENTIC-DELIVERY.md`](docs/AGENTIC-DELIVERY.md)
- 2026 master-plan issue wave:
  - GitHub `#13` / Linear `BC-221`: voice inbox and capture handoff
  - GitHub `#14` / Linear `BC-222`: KB inventory and health audit
  - GitHub `#15` / Linear `BC-223`: retrieval inspector
  - GitHub `#16` / Linear `BC-224`: recipe manifests and command palette
  - GitHub `#17` / Linear `BC-226`: composition studio
  - GitHub `#18` / Linear `BC-225`: transcription/provider privacy matrix
  - GitHub `#19` / Linear `BC-227`: eval scorecards
  - GitHub `#20` / Linear `BC-228`: agentic handoff exports
  - GitHub `#21` / Linear `BC-229`: run artifact workspace
  - GitHub `#22` / Linear `BC-230`: profile operating system
  - GitHub `#23` / Linear `BC-231`: resurfacing digest
  - GitHub `#24` / Linear `BC-232`: SongForge lyric/prompt-pack mode

## Known Risks

- `tests/smoke.sh` needs a free localhost port; the default is `8599`.
- Runtime MP3/M4A operations still need `ffmpeg` on `PATH`; unit fixtures use
  WAV so local tests can run without it.
- Services-mode transcription still returns text-only details, so timestamped
  chapter segments are not yet available over HTTP.
- The new GitHub issues were intentionally created without `agent:ready` so
  the swarm does not start until the wave is reviewed. Add `agent:ready` when
  ready to trigger the agentic dev loop.
- Agentic GitHub workflows depend on labels and issue-body quality. Ready
  issues must keep the required sections in `docs/AGENTIC-DELIVERY.md`.
- GitHub/Linear state can drift quickly; refresh live tracker state before
  closing issues or claiming a swarm lane is finished.
