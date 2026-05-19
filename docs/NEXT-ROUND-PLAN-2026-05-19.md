# WhisperForge Next Round Plan

Date: 2026-05-19

## Current State

WhisperForge is consolidated into `WalksWithASwagger/spektorAI`.

- Legacy audio repositories are archived.
- Only `origin/main` remains for this repo after branch cleanup.
- Local stale detached Codex worktrees were removed.
- GitHub issues `#37` through `#40` are closed.
- No open PRs remain.
- Issue `#36` remains open because the license decision needs a human.
- Current verification baseline is `239 passed`, plus eval fixture, UI smoke,
  Streamlit health smoke, JSON validation, and whitespace checks.

## Next Round Recommendation

### 1. Close The Human-Gated Brand/License Issue

Resolve `#36` before creating another broad implementation wave.

Decision needed: should `spektorAI` get an explicit license? Recommended
default is MIT if the goal is public reuse and agent friendliness; choose no
license/private-proprietary only if the repo should not be freely reused.

### 2. Dogfood A Real Wispr Flow Capture

Run one real capture through the current product loop:

- save/import the capture,
- run a practical recipe,
- inspect review receipts and scorecards,
- export markdown or Notion,
- reopen the run,
- generate the resurfacing digest,
- record friction and missing affordances.

This should produce a short session report before more architecture work.

### 3. Add End-To-End UI Coverage

After dogfooding identifies the true primary path, add browser or Streamlit
interaction coverage for that path. Start with paste/import -> recipe run ->
review -> markdown/vault export -> run reopen.

### 4. Pick The Release Target

Choose one target for the next milestone:

- local-first personal workbench,
- private hosted Streamlit app,
- services-mode deployment,
- packageable desktop/local workflow.

This decides how much auth, storage, Docker parity, and Notion behavior matter
now.

## Candidate Issue Wave

Create these only after the dogfood report and release-target decision are
clear:

| ID | Priority | Title | Gate |
| --- | --- | --- | --- |
| `wf-license-brand-closeout` | P0 | Close license, repo metadata, and brand cleanup | Human chooses license posture |
| `wf-dogfood-loop` | P0 | Run and document a real Wispr Flow-to-output session | Human supplies capture/export target |
| `wf-e2e-primary-loop` | P0 | Add end-to-end coverage for the chosen primary loop | Dogfood path identified |
| `wf-release-target` | P0 | Decide and document the next release target | Human chooses target |
| `wf-provider-router-capabilities` | P1 | Add provider-router capability metadata and fixtures | Large-file evaluation accepted |
| `wf-kb-governance` | P1 | Add canonical KB pack and stale/private review workflow | Human confirms policy |
| `wf-human-approved-routing` | P1 | Add preview-and-approve routing for GitHub/Linear/Notion/follow-ups | Approval boundary confirmed |

## Not Yet

- Do not add new transcription providers before router capability fixtures.
- Do not automate digest routing before approval UI/CLI exists.
- Do not build hosted/multi-user auth until the release target says hosted.
- Do not expand SongForge into direct music-generation service calls before the
  text workflow has real-session feedback.
