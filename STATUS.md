# WhisperForge Status

Last updated: 2026-05-24

## Current State

- Current branch: `main`, synced with `origin/main`.
- Latest feature baseline: the merged local-first reliability swarm for KB
  governance, transcription-router media planning, approved digest routing, and
  SongForge export polish on current `main`.
- GitHub repo: `WalksWithASwagger/spektorAI`.
- GitHub metadata: description, topics, and homepage point to this canonical
  WhisperForge repo.
- License posture: no open-source license is currently granted; do not inherit
  the archived `whisperforge` MIT license without an explicit owner decision.
- Live GitHub queue: no open issues and no open PRs as of 2026-05-24 after
  merging PRs `#53` through `#56`.
- 2026 master-plan wave: GitHub `#13` through `#24` are closed and their
  corresponding Linear issues were moved to Done during delivery closeout.
- Primary product surface: direct Streamlit mode via `make app`.
- Services mode: still present through `docker compose`; direct mode remains
  the product lead unless service parity is the explicit scope.
- Release target decision (owner): local-first personal workbench (`#42`).
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
- Dogfood report:
  [`docs/dogfood/2026-05-20-wispr-flow-loop.md`](docs/dogfood/2026-05-20-wispr-flow-loop.md).

## Verified Baseline

- Verified on 2026-05-24.
- `git status --short --branch` -> clean `main...origin/main`.
- `git rev-list --left-right --count HEAD...@{u}` -> `0 0`.
- `gh issue list --state open --limit 100` -> no open issues.
- `gh pr list --state open --limit 20` -> no open PRs.
- `git branch -r` -> `origin/main` plus the default `origin/HEAD` pointer.
- `git worktree list --porcelain` -> only `/Users/kk/Code/spektorAI` remains
  for this repo after removing stale detached Codex worktrees.
- `git ls-files whisperforge-env venv .cache __pycache__ .pytest_cache | wc -l`
  -> `0`.
- `python3 -m json.tool ops/roadmap/features.json` passes.
- `make docs-check` passes documentation link, command reference, and freshness
  checks.
- `make lint` passes dependency-light Python syntax checks.
- `make test` -> `301 passed`.
- `make browser-e2e` -> `browser-e2e: OK`.
- `make browser-e2e-fresh` -> `browser-e2e-fresh: OK`.
- `make eval-fixture` -> editorial and SongForge fixtures pass.
- `venv/bin/python tests/ui_smoke.py` -> rendered Streamlit shell smoke passes
  (bare-mode `ScriptRunContext` warnings are expected in this harness).
- `make smoke` passes Streamlit health smoke on the default smoke port.
- `make digest` -> `.cache/digests/2026-05-24-resurfacing-digest.md`.
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
- Dogfood report: [`docs/dogfood/2026-05-20-wispr-flow-loop.md`](docs/dogfood/2026-05-20-wispr-flow-loop.md)

## Known Risks

- The app now has two Playwright-driven localhost smokes against a real
  Streamlit subprocess: `make browser-e2e` covers run-history reopen plus
  markdown export, and `make browser-e2e-fresh` covers the fresh-run
  paste -> recipe -> review -> export loop. The fresh-run smoke now uses
  recorded fixture payloads from
  `tests/fixtures/browser_e2e_fresh_run.json` via
  `WHISPERFORGE_E2E_FIXTURE_PATH`, so the loop runs hermetically without
  provider credentials.
- Services-mode now forwards transcription `segments` and `language` over HTTP
  when the backend emits rich details; non-rich backends still return empty
  segment lists by design.
- The transcription/provider matrix now has a fixture-backed media planning
  layer (`#50`) with opt-in ffprobe inspection, planned-only FFmpeg
  normalization, and visible privacy/cost receipts. Runtime transcription
  defaults remain unchanged.
- SongForge is intentionally text-first and deterministic. It now emits
  structure variants and originality guardrails, but it is still not an
  audio/music-generation integration.
- Resurfacing digest is report-only by default. Approved local follow-up queue
  and Notion draft routing now exist (`#51`), but outbound routing still needs
  explicit approval and config.
- Agent handoff drafts now support approval-gated GitHub/Linear creation plus
  local follow-up queue routing via `whisperforge_core.handoff_router`. Default
  remains dry-run when target config is missing;
  `WHISPERFORGE_HANDOFF_DRY_RUN=1` is a forced-dry-run kill switch for demos
  and tests.
- Dogfood follow-ups `#45`, `#46`, and `#47` are now shipped: digest filtering
  for non-prod noise, capture-status metadata sync, and export-aware scorecard
  readiness refresh.
- GitHub/Linear state can drift quickly; refresh live tracker state before
  creating or closing new roadmap work.
- Legacy audio repos are being archived as pointers to this canonical repo;
  do not pull their stale architecture into `spektorAI` without a scoped issue.

## Next Round

Dogfood closeout, first router slice, Run Story/Review extraction, the demo
fixture pack, Review polish, KB governance, router media planning, approved
digest routing, and SongForge export polish are complete. The next roadmap
slice should be created from fresh dogfood evidence rather than reopening the
now-closed `#49` through `#52` queue.
