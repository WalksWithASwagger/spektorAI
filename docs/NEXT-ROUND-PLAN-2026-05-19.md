# WhisperForge Next Round Plan

Date: 2026-05-19

## Current State

WhisperForge is consolidated into `WalksWithASwagger/spektorAI`.

- Legacy audio repositories are archived.
- Only `origin/main` remains for this repo after branch cleanup.
- Local stale detached Codex worktrees were removed.
- GitHub issues `#36` through `#40` are closed.
- No open PRs remain.
- GitHub metadata points to this canonical WhisperForge repo.
- No open-source license is currently granted; the archived `whisperforge` MIT
  license is not inherited without an explicit owner decision.
- Current verification baseline is `244 passed`, plus eval fixture, UI smoke,
  Streamlit health smoke, JSON validation, and whitespace checks.

## Next Round Recommendation

### 1. Dogfood A Real Wispr Flow Capture

Run one real capture through the current product loop:

- save/import the capture,
- run a practical recipe,
- inspect review receipts and scorecards,
- export markdown or Notion,
- reopen the run,
- generate the resurfacing digest,
- record friction and missing affordances.

This should produce a short session report before more architecture work.

### 2. Add End-To-End UI Coverage

After dogfooding identifies the true primary path, add browser or Streamlit
interaction coverage for that path. Start with paste/import -> recipe run ->
review -> markdown/vault export -> run reopen.

### 3. Pick The Release Target

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
