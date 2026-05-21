# Audio Repo Consolidation Audit

Date: 2026-05-18

Historical snapshot: use `STATUS.md`, `ROADMAP.md`, and
`docs/NEXT-ROUND-PLAN-2026-05-19.md` for current repo state, verification
counts, and active roadmap work.

## Decision

`WalksWithASwagger/spektorAI` is the canonical WhisperForge repository.

The product name stays `WhisperForge`. The repository name stays `spektorAI`
for this pass because it is the active, tested implementation and already owns
the current roadmap, delivery workflow, run artifacts, and issue history.

The legacy repositories should be archived, not deleted, after their README
files point agents and humans back to the canonical repo:

- `WalksWithASwagger/audio-transcription-studio`
- `WalksWithASwagger/audio-wisdom-harvester`
- `WalksWithASwagger/whisperforge`

This pass is roadmap-level salvage only. No legacy runtime code should be
copied into the canonical app until a real dogfood session proves the need.

## Canonical Repo

Repository: `WalksWithASwagger/spektorAI`

Verified state entering this consolidation pass:

- Branch: `main`
- Remote sync: `git rev-list --left-right --count main...origin/main` returned
  `0 0`.
- Baseline commit: `99e5287 docs: refresh WhisperForge audit roadmap`
- Open GitHub issues: none at audit time.
- Open GitHub PRs: none at audit time.
- Tracked files before this consolidation artifact: 414.
- Verification at audit time: `make test` passed with 229 tests, plus
  `make eval-fixture`, `venv/bin/python tests/ui_smoke.py`, `make smoke`,
  `python3 -m json.tool ops/roadmap/features.json`, and `git diff --check`.

What makes it canonical:

- It has the current capture inbox, recipe command palette, source-grounded
  review, scorecards, handoff drafts, run workspace, resurfacing digest, and
  SongForge mode.
- It has the active docs and roadmap registry.
- It has the only clean current GitHub queue.
- It already treats Wispr Flow text as the primary capture layer instead of
  trying to compete with dictation overlays.

## Legacy Inventory

### `audio-transcription-studio`

Status: private legacy experiment.

Shape:

- Flask plus Socket.IO backend with a React/Vite frontend.
- Queue, upload, progress, and watch-folder ideas.
- Knowledge-base manager, scanner, content aggregator, synthesis engine, and
  markdown-oriented output planning.
- Docs describe an Obsidian-friendly transcript vault, weekly recaps, topic
  summaries, people tracking, project tracking, and action aggregation.
- Three open draft PRs were present at audit time:
  `#1`, `#2`, and `#3`.

Salvage:

- Watch-folder or import-folder intake.
- Batch queue semantics for multiple audio/text captures.
- Obsidian/markdown vault organization.
- Weekly recap generation.
- Topic evolution summaries.
- People/action/project aggregation.

Do not import:

- The Flask/Socket.IO/React architecture.
- The queue implementation directly; it is simple mutable JSON state and does
  not match the canonical run-artifact model.

### `audio-wisdom-harvester`

Status: private legacy prototype.

Shape:

- Lovable/Vite/React/shadcn-style frontend.
- TypeScript services for transcription, content generation, Notion, Zapier,
  and Supabase.
- The core transcription/content/Notion services are mocks or placeholders.
- No open issues or PRs were present at audit time.

Salvage:

- Prompt names and output categories such as insight extraction, LinkedIn post,
  thread, illustration prompt, blog outline, full article, and SEO pass.
- UI ideas around editor review, prompt selection, file history, and connector
  setup.

Do not import:

- Mock service implementations.
- Supabase or Zapier scaffolding before the canonical product chooses a release
  target and routing policy.

### `whisperforge`

Status: public legacy implementation and brand surface.

Shape:

- Public repo with the `whisperforge` name, MIT license, homepage metadata, and
  useful transcription topics.
- Older Streamlit app with large monolithic `app_simple.py`, Supabase/Notion
  assumptions, Aurora styling, prompt/template files, and large-file docs.
- Three open PRs were present at audit time:
  `#16`, `#17`, and `#18`.

Salvage:

- Public brand metadata: name, description, homepage, topics, and license
  decision input.
- FFmpeg large-file processing strategy: validation, ffprobe inspection,
  chunking, parallel transcription, transcript assembly, and graceful fallback.
- Prompt/template taxonomy if it still improves canonical recipes.

Do not import:

- The monolithic Streamlit app.
- Supabase account/storage assumptions.
- Old PRs wholesale; treat them as historical context unless a current issue
  names a specific idea to rebuild natively.

## Salvage Wave

The first canonical issue wave should turn the useful material into explicit
future work:

| ID | Issue | Priority | Title | Source |
| --- | --- | --- | --- | --- |
| `wf-brand-metadata-cleanup` | #36 | P0 | Finish public brand, repo metadata, and license decision | `whisperforge`; shipped without adding a license file |
| `wf-watch-folder-inbox` | #37 | P1 | Add watch-folder/import-folder capture intake | `audio-transcription-studio` |
| `wf-knowledge-synthesis` | #38 | P1 | Add weekly recaps and topic evolution summaries | `audio-transcription-studio` |
| `wf-large-file-router-eval` | #39 | P1 | Evaluate FFmpeg large-file handling for provider router | `whisperforge`; see `docs/LARGE-FILE-ROUTER-EVALUATION-2026-05-19.md` |
| `wf-markdown-vault-export` | #40 | P2 | Add Obsidian-friendly markdown vault export | `audio-transcription-studio` |

These issues should reference this audit and stay scoped to canonical
`spektorAI` implementation. Legacy code can be read for context, but new code
belongs in `spektorAI` and must follow the existing run/capture/provider
patterns.

## Archive Plan

1. Land this audit in `spektorAI` and push it to `main`.
2. Create the salvage issue wave in `WalksWithASwagger/spektorAI`.
3. Update the README in each legacy repo with a clear archived/superseded
   notice pointing to `https://github.com/WalksWithASwagger/spektorAI`.
4. Comment on and close stale legacy PRs as superseded by this consolidation.
5. Archive the three legacy repositories in GitHub so they are read-only.

## What Not To Do

- Do not delete legacy repos in this pass.
- Do not merge the legacy PRs into their old repositories.
- Do not copy stale architectures into the canonical app.
- Do not rename the canonical repo until the user explicitly chooses a repo
  rename/move plan.
- Do not enable external routing from salvage issues without the existing
  human-approval boundary.
