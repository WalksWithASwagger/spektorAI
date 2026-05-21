# WhisperForge Audit And Roadmap

Date: 2026-05-18

Historical snapshot: use `STATUS.md`, `ROADMAP.md`, and
`docs/NEXT-ROUND-PLAN-2026-05-19.md` for the current verification baseline and
active workplan.

## Executive Read

WhisperForge is in a much better place than it was at the start of the reset.
The product is no longer "transcribe audio and hope a prompt makes content."
It now has the bones of an operating system for spoken thought: capture,
knowledge grounding, recipes, review, scorecards, handoffs, run recovery,
resurfacing, and a bounded creative lane.

The next risk is not missing features. The next risk is diffusion. The right
move is to dogfood one complete workflow, choose the release target, and add
the missing end-to-end proof around the UI path real humans will use.

## Audit Scope

- Local repository state in `/Users/kk/Code/spektorAI`.
- Live GitHub issue and PR state for `WalksWithASwagger/spektorAI`.
- Root docs, master plan, delivery docs, backlog registry, tests, scripts,
  Streamlit UI modules, services, and shared core modules.
- Local generated clutter under Python and pytest cache directories.

## Current Verified Facts

- Branch: `main`.
- Consolidation baseline:
  `99e5287 docs: refresh WhisperForge audit roadmap`.
- Sync: `git rev-list --left-right --count HEAD...@{u}` returned `0 0`.
- GitHub open issues: none.
- GitHub open PRs: none.
- Tracked files before the audio-repo consolidation artifact: 414.
- Python files under `whisperforge_core`, `ui`, `services`, `scripts`, and
  `tests`: 80.
- Tracked venv/cache files: 0.
- Generated Python and pytest cache directories were removed during cleanup.

## What Is Now Solid

### Product Loop

Capture, recipe selection, output generation, review, export, handoff draft,
run reopen, and resurfacing now share durable metadata instead of each feature
living in its own corner.

### Knowledge Grounding

The KB is no longer invisible prompt soup. The repo now has KB inventory,
health warnings, retrieval inspection, source receipts, review summaries, and
scorecards that make grounding inspectable.

### Agentic Delivery

The GitHub/Linear workflow, issue contract, labels, linter, PR review bot, and
handoff draft format are coherent. The previous issue wave was completed
without leaving open tracker work behind.

### Recovery And Audit Trail

Run manifests and stage artifacts mean outputs can be reopened and safe
downstream exports can be retried without rerunning expensive generation.

### Creative Lane

SongForge exists at the right first level: text-first, source-linked,
service-agnostic, and explicit about originality and no living-artist
imitation.

## Gaps And Risks

### End-To-End UX Proof

`make test`, service contracts, eval fixtures, shell render smoke, and health
smoke are strong, but they do not yet prove the complete user journey through
Streamlit controls and session state.

### Release Target Ambiguity

The product can run locally and has services mode, but the next milestone
depends on whether this is meant to be a personal local workbench, hosted
private app, services deployment, or packageable desktop/local workflow.

### Cross-Repo Identity Drift

Three older audio-related repositories existed alongside this canonical repo:
`audio-transcription-studio`, `audio-wisdom-harvester`, and `whisperforge`.
The consolidation decision is documented in
[`AUDIO-REPO-CONSOLIDATION-AUDIT-2026-05-18.md`](AUDIO-REPO-CONSOLIDATION-AUDIT-2026-05-18.md):
keep `spektorAI` as canonical, preserve the product name `WhisperForge`,
salvage roadmap ideas only, and archive the legacy repos after README pointers.

### Services Parity Boundary

Services mode payload contracts are pinned, but transcription over HTTP still
returns text-only details. Timestamped chapters and richer segment metadata are
not fully service-parity features yet.

### Provider Matrix Is Not A Router

The transcription provider matrix is useful strategy, not runtime behavior.
Any switch toward diarization, local privacy, or streaming still needs router
implementation and fixtures.

### KB Governance Needs Human Policy

The code can detect stale, duplicate, oversized, empty, and private-looking
files. It cannot decide which docs are canonical, what should be excluded, or
how aggressively stale context should be quarantined.

### Routing Is Intentionally Human-Gated

Handoff drafts and resurfacing digests stop before external action. That is
the right safety boundary, but the next version needs an explicit approval
flow if it should create GitHub/Linear issues, follow-ups, or notifications.

## Roadmap Recommendation

### Phase A: Dogfood And Stabilize

Run real Wispr Flow captures through the full loop. Capture friction, export
quality, scorecard usefulness, and run-reopen behavior. This should produce a
short session report and only then the next issue wave.

Candidate work:

- `wf-dogfood-loop`: real capture-to-output session report.
- `wf-e2e-browser`: browser/Streamlit interaction coverage for paste input,
  recipe run, review rendering, markdown export, run reopen, and digest.
- `wf-release-target`: decide and document the next deploy/package target.

### Phase B: Operational Trust

Make the product safer to run repeatedly with the real KB and external
handoff surfaces.

Candidate work:

- `wf-kb-governance`: canonical KB packs, sensitive-file policy, stale-file
  review workflow, profile migration notes.
- `wf-handoff-routing`: explicit review/approval before GitHub, Linear,
  follow-up, or notification creation.
- `wf-digest-automation`: optional report-only schedule with explicit
  destination and no external routing unless enabled.

### Phase C: Better Inputs And Creative Outputs

Improve high-value edges after the product loop is proven.

Candidate work:

- `wf-transcription-router`: runtime provider router from the matrix with
  diarization/timestamps/privacy fixtures.
- `wf-songforge-polish`: optional LLM polish and export presets for the
  source-linked SongForge pack.
- `wf-recipe-templates`: more first-class recipes for client brief, newsletter
  issue, talk notes, follow-up queue, and GitHub issue wave.

## Verification Run

- `python3 -m json.tool ops/roadmap/features.json` passed.
- `git diff --check` passed.
- At audit time, `make test` passed: 229 tests, with four third-party `pydub`
  SyntaxWarnings.
- `make eval-fixture` passed editorial and SongForge fixture checks.
- `venv/bin/python tests/ui_smoke.py` passed rendered shell smoke.
- `make smoke` passed Streamlit health smoke on port `8599`.

## Human Questions

1. What is the next release target: local personal app, private hosted
   Streamlit, services-mode deployment, or packageable desktop/local workflow?
2. Should WhisperForge keep Wispr Flow as the assumed capture layer, or should
   it watch/import from a folder, clipboard, or text-file inbox automatically?
3. What is the default export destination for real work: Notion, markdown vault,
   GitHub/Linear, or some combination?
4. Which KB files are canonical, and which categories should be private,
   quarantined, or excluded from generation?
5. For transcription, do you care most about local privacy, diarization,
   timestamps, streaming, proper nouns, or lowest cost?
6. Should resurfacing stay manual/report-only, or do you want a recurring
   digest? If recurring, where should it land?
7. Should handoff routing be allowed to create GitHub/Linear issues after a
   preview, or should it remain draft-only for now?
8. What do you actually want SongForge for first: personal creative play,
   event recap songs, spoken-word scripts, social prompts, or real music-tool
   prompt packs?

## Suggested Immediate Next Step

Do one dogfood session before creating another large issue wave. The repo is
now capable enough that the highest-signal input is lived friction: paste a
real Wispr Flow capture, run the best-fit recipe, export it, reopen the run,
generate a digest, and write down what felt clumsy.
