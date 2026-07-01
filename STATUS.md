# WhisperForge Status

Last updated: 2026-07-01

## Current State

- Current branch: `main`, synced with `origin/main` at the start of the
  shutdown pass.
- Latest product/code baseline before this shutdown note:
  `ca4355d26f5b3a452d504da9f420b8c9542b4f67` (`Add lightweight company OS
  manifest`).
- Latest feature baseline: the merged local-first reliability swarm for KB
  governance, transcription-router media planning, approved digest routing, and
  SongForge export polish on current `main`.
- GitHub repo: `WalksWithASwagger/spektorAI`.
- GitHub metadata: description, topics, and homepage point to this canonical
  WhisperForge repo.
- License posture: no open-source license is currently granted; do not inherit
  the archived `whisperforge` MIT license without an explicit owner decision.
- Live GitHub queue: no open issues and no open PRs as of 2026-05-30 after
  merging PRs `#53` through `#57`.
- Staging/deploy status: not applicable for this shutdown. No repo-defined
  staging deployment command was found; `make smoke` is the local Streamlit
  health check.
- 2026 master-plan wave: GitHub `#13` through `#24` are closed and their
  corresponding Linear issues were moved to Done during delivery closeout.
- Primary product surface: direct Streamlit mode via `make app`.
- Services mode: still present through `docker compose`; direct mode remains
  the product lead unless service parity is the explicit scope.
- Release target decision (owner): local-first personal workbench (`#42`).
- Next round plan:
  [`docs/NEXT-ROUND-PLAN-2026-05-19.md`](docs/NEXT-ROUND-PLAN-2026-05-19.md).
- Presentation runbook:
  [`docs/PRESENTATION-RUNBOOK-2026-05-19.md`](docs/PRESENTATION-RUNBOOK-2026-05-19.md).
- Dogfood report:
  [`docs/dogfood/2026-05-20-wispr-flow-loop.md`](docs/dogfood/2026-05-20-wispr-flow-loop.md).

## Verified Baseline

- Verified on 2026-05-30 during shutdown closeout.
- `git fetch origin --prune` completed successfully.
- `git status --short --branch` -> clean `main...origin/main` before docs
  edits.
- `git rev-list --left-right --count HEAD...@{u}` -> `0 0`.
- `git ls-remote origin refs/heads/main` ->
  `ca4355d26f5b3a452d504da9f420b8c9542b4f67`.
- `gh issue list --state open --limit 50 --json number,title,labels,updatedAt,url`
  -> `[]`.
- `gh pr list --state open --limit 20 --json number,title,headRefName,baseRefName,isDraft,mergeStateStatus,updatedAt,url`
  -> `[]`.
- `gh pr list --state all --head codex/add-company-os-manifest --limit 5`
  -> PR `#57` is merged.
- `git branch -r` -> `origin/main`, `origin/HEAD`, and the preserved merged
  `origin/codex/add-company-os-manifest` branch.
- `git worktree prune` completed successfully after a stale detached worktree
  path was found missing.
- `git worktree list --porcelain` -> only `/Users/kk/Code/spektorAI` remains
  for this repo.
- `git ls-files whisperforge-env venv .cache __pycache__ .pytest_cache | wc -l`
  -> `0`.
- `python3.11 -m venv venv` restored the expected ignored local environment.
- `venv/bin/python -m pip install --upgrade pip` passed.
- `venv/bin/python -m pip install -r requirements-dev.txt` passed.
- `git diff --check` passes.
- `python3 -m json.tool ops/roadmap/features.json >/dev/null` passes.
- `make docs-check` passes documentation link, command reference, and freshness
  checks.
- `make lint` passes Python syntax and high-signal Ruff checks.
- `make test` -> `302 passed, 2 warnings`.
- `make pip-check` -> `No broken requirements found`.
- `make eval-fixture` -> editorial and SongForge fixtures pass.
- `make smoke` passes Streamlit health smoke on the default smoke port.

## Shutdown Handoff - 2026-05-30

- What changed today: restored the ignored `venv/` expected by the Makefile,
  reran the closeout gates, and updated this shutdown handoff. No product code,
  API, schema, runtime default, deployment, or user-facing behavior changed.
- Completed: repo sync and live GitHub queue checks, stale worktree metadata
  prune, local dependency repair, docs truth check, lint, unit tests, dependency
  consistency check, fixture eval, Streamlit health smoke, and docs-only handoff
  update.
- Unfinished: no active repo work is intentionally left unfinished.
- Known weirdness: before rebuilding `venv/`, default `make test` and
  `make smoke` failed because `venv/bin/python` did not exist; the existing
  ignored `whisperforge-env/` also lacked `pip`, `pytest`, `ruff`, and
  `streamlit`. The repaired `venv/` is intentionally ignored.
- Test warnings: `make test` reports the existing `pydub` `audioop`
  deprecation warning for Python 3.13 and a Starlette `httpx` deprecation
  warning. Both are non-blocking in the 2026-05-30 closeout.
- Important files touched: `STATUS.md` and `ROADMAP.md`.
- Decision/assumption: staging is not applicable; the local Streamlit health
  smoke is the appropriate shutdown confidence check for this local-first app.
- Recommended next step: start from this file, activate `venv/`, and rerun
  `make docs-check && make lint && make test && make smoke` before opening a new
  feature lane.

## Docs And Structure Audit - 2026-07-01

- Scope: documentation and directory-structure cleanup only. No product code,
  API, schema, runtime default, or user-facing behavior changed.
- Removed the unused vendored Fabric `patterns/` tree (256 files). Nothing in
  the codebase, `Makefile`, CI, or docs referenced it; the app's prompts live
  under `prompts/<user>/` via `whisperforge_core/prompts.py`.
- Retired four superseded historical docs that already redirected readers to the
  living `STATUS.md`/`ROADMAP.md`/`NEXT-ROUND-PLAN` set: the 2026-05-17
  documentation audit, the audio-repo consolidation audit, the audit-and-roadmap
  snapshot, and the 2026-05-18 master plan. Their record survives in
  `changelog.md` and git history.
- Rewired inbound links in `ROADMAP.md`, `STATUS.md`,
  `docs/LINEAR-GITHUB-PIPELINE.md`, `.company-os/project.yaml`, and
  `ops/roadmap/features.json` to the living docs so `make docs-check` stays green.
- Delivery: shipped on branch `claude/docs-project-audit-tn76u2` as PR `#59`.
  All checks green (`docs-check`, `python`; `review` skipped); awaiting owner
  merge. Short-horizon sequencing lives in
  [`docs/WEEK-PLAN-2026-07-01.md`](docs/WEEK-PLAN-2026-07-01.md).

## Active Handles

- Roadmap: [`ROADMAP.md`](ROADMAP.md)
- Status: [`STATUS.md`](STATUS.md)
- This week: [`docs/WEEK-PLAN-2026-07-01.md`](docs/WEEK-PLAN-2026-07-01.md)
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
