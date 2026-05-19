# WhisperForge Status

Last updated: 2026-05-19

## Current State

- Current branch: `main`, synced with `origin/main`.
- Latest shipped feature baseline:
  `2a7e658 feat: ship audio consolidation salvage wave`.
- GitHub repo: `WalksWithASwagger/spektorAI`.
- GitHub metadata: description, topics, and homepage point to this canonical
  WhisperForge repo.
- License posture: no open-source license is currently granted; do not inherit
  the archived `whisperforge` MIT license without an explicit owner decision.
- Live GitHub queue: audio consolidation issues `#36` through `#40` have
  shipped. No open PRs at closeout time.
- 2026 master-plan wave: GitHub `#13` through `#24` are closed and their
  corresponding Linear issues were moved to Done during delivery closeout.
- Primary product surface: direct Streamlit mode via `make app`.
- Services mode: still present through `docker compose`; direct mode remains
  the product lead unless service parity is the explicit scope.
- Strategy anchor:
  [`docs/WHISPERFORGE-MASTER-PLAN-2026-05-18.md`](docs/WHISPERFORGE-MASTER-PLAN-2026-05-18.md).
- Current audit and from-here roadmap:
  [`docs/WHISPERFORGE-AUDIT-AND-ROADMAP-2026-05-18.md`](docs/WHISPERFORGE-AUDIT-AND-ROADMAP-2026-05-18.md).
- Audio repo consolidation audit:
  [`docs/AUDIO-REPO-CONSOLIDATION-AUDIT-2026-05-18.md`](docs/AUDIO-REPO-CONSOLIDATION-AUDIT-2026-05-18.md).
- Next round plan:
  [`docs/NEXT-ROUND-PLAN-2026-05-19.md`](docs/NEXT-ROUND-PLAN-2026-05-19.md).
- Presentation runbook:
  [`docs/PRESENTATION-RUNBOOK-2026-05-19.md`](docs/PRESENTATION-RUNBOOK-2026-05-19.md).

## Verified Baseline

- `git status --short --branch` -> clean `main...origin/main`.
- `git rev-list --left-right --count HEAD...@{u}` -> `0 0`.
- `gh issue list --state open --limit 20` -> no open issues after `#36`
  closeout.
- `gh pr list --state open --limit 50` -> no open PRs.
- `git branch -r` -> only `origin/main` remains after pruning merged legacy
  PR branches.
- `git worktree list --porcelain` -> only `/Users/kk/Code/spektorAI` remains
  for this repo after removing stale detached Codex worktrees.
- `git ls-files whisperforge-env venv .cache __pycache__ .pytest_cache | wc -l`
  -> `0`.
- `python3 -m json.tool ops/roadmap/features.json` passes.
- `make test` -> `242 passed`.
- `make eval-fixture` passes editorial and SongForge fixtures.
- `venv/bin/python tests/ui_smoke.py` passes rendered Streamlit shell smoke.
- `make smoke` passes Streamlit health smoke on the default smoke port.
- `git diff --check` passes.

## Active Handles

- Roadmap: [`ROADMAP.md`](ROADMAP.md)
- Status: [`STATUS.md`](STATUS.md)
- Current audit: [`docs/WHISPERFORGE-AUDIT-AND-ROADMAP-2026-05-18.md`](docs/WHISPERFORGE-AUDIT-AND-ROADMAP-2026-05-18.md)
- Audio repo consolidation: [`docs/AUDIO-REPO-CONSOLIDATION-AUDIT-2026-05-18.md`](docs/AUDIO-REPO-CONSOLIDATION-AUDIT-2026-05-18.md)
- Master plan: [`docs/WHISPERFORGE-MASTER-PLAN-2026-05-18.md`](docs/WHISPERFORGE-MASTER-PLAN-2026-05-18.md)
- Delivery workflow: [`docs/LINEAR-GITHUB-PIPELINE.md`](docs/LINEAR-GITHUB-PIPELINE.md)
- Backlog registry: [`ops/roadmap/features.json`](ops/roadmap/features.json)
- Agentic contract: [`docs/AGENTIC-DELIVERY.md`](docs/AGENTIC-DELIVERY.md)
- Provider matrix: [`docs/TRANSCRIPTION-PROVIDER-MATRIX-2026-05-18.md`](docs/TRANSCRIPTION-PROVIDER-MATRIX-2026-05-18.md)
- Large-file router evaluation: [`docs/LARGE-FILE-ROUTER-EVALUATION-2026-05-19.md`](docs/LARGE-FILE-ROUTER-EVALUATION-2026-05-19.md)
- Next round plan: [`docs/NEXT-ROUND-PLAN-2026-05-19.md`](docs/NEXT-ROUND-PLAN-2026-05-19.md)
- Presentation runbook: [`docs/PRESENTATION-RUNBOOK-2026-05-19.md`](docs/PRESENTATION-RUNBOOK-2026-05-19.md)

## Known Risks

- The app has solid unit, service-contract, eval-fixture, rendered-shell, and
  health checks, but it still needs an end-to-end browser test for the full
  Wispr Flow paste -> recipe -> review -> export loop.
- Services-mode tests pin the payload contract, but `services/transcription`
  still returns text-only details over HTTP, so timestamped segment parity is
  not complete.
- The transcription/provider matrix is a decision artifact; runtime provider
  routing still needs implementation and real audio fixtures before defaults
  should change.
- SongForge is intentionally text-first and deterministic. It is ready as a
  source-linked creative pack, not as an audio/music-generation integration.
- Resurfacing digest is report-only. Any notification, publishing, routing, or
  recurring automation needs explicit human approval.
- GitHub/Linear state can drift quickly; refresh live tracker state before
  creating or closing new roadmap work.
- Legacy audio repos are being archived as pointers to this canonical repo;
  do not pull their stale architecture into `spektorAI` without a scoped issue.

## Next Round

Run a real Wispr Flow dogfood session before creating the next broad issue
wave. The durable plan is in
[`docs/NEXT-ROUND-PLAN-2026-05-19.md`](docs/NEXT-ROUND-PLAN-2026-05-19.md).
