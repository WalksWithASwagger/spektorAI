# WhisperForge Roadmap

Last reviewed: 2026-05-19

The May 2026 reset wave is now complete. The strategic anchor remains
[`docs/WHISPERFORGE-MASTER-PLAN-2026-05-18.md`](docs/WHISPERFORGE-MASTER-PLAN-2026-05-18.md);
the current audit and from-here plan is
[`docs/WHISPERFORGE-AUDIT-AND-ROADMAP-2026-05-18.md`](docs/WHISPERFORGE-AUDIT-AND-ROADMAP-2026-05-18.md).
The immediate next-round plan is
[`docs/NEXT-ROUND-PLAN-2026-05-19.md`](docs/NEXT-ROUND-PLAN-2026-05-19.md).

## Current Product Shape

WhisperForge is now a single-user voice-to-knowledge workbench:

- capture inbox for Wispr Flow text, notes, uploads, and recordings;
- profile/KB audit, retrieval inspection, RAG benchmarking, and profile OS
  metadata;
- recipe command palette for repeatable article, social, issue-handoff, and
  SongForge workflows;
- source-grounded review surface with receipts, excerpts, scorecards, claim
  flags, compare/persona variants, and handoff drafts;
- local run workspace with manifests, stage artifacts, reopen, and downstream
  export retry;
- local report-only resurfacing digest;
- text-first SongForge creative pack mode.

## Delivery State

- GitHub issues `#13` through `#24`: closed.
- Audio consolidation issues `#37` through `#40`: closed.
- Pull requests `#25` through `#35`: merged.
- Current shipped baseline:
  `2a7e658 feat: ship audio consolidation salvage wave`.
- Open GitHub issues: `#36` for the license/metadata human decision.
- Open GitHub PRs: none.
- Current unit baseline: `239 passed`.
- Audio repo consolidation audit:
  [`docs/AUDIO-REPO-CONSOLIDATION-AUDIT-2026-05-18.md`](docs/AUDIO-REPO-CONSOLIDATION-AUDIT-2026-05-18.md).
  Next round plan:
  [`docs/NEXT-ROUND-PLAN-2026-05-19.md`](docs/NEXT-ROUND-PLAN-2026-05-19.md).

## Roadmap From Here

### 1. Dogfood The Full Loop

Run real Wispr Flow captures through the whole system and measure friction:
capture inbox, recipe selection, review, markdown/Notion export, handoff draft,
run reopen, and resurfacing digest.

Success looks like a documented session report with concrete UX gaps, not more
architecture.

### 2. Add End-To-End Browser Coverage

The test suite is broad, but the riskiest product surface is still the rendered
Streamlit workflow. Add browser-level or Streamlit interaction tests that prove
the primary loop works with real UI state transitions.

Focus first on paste input, recipe run, review tab rendering, markdown export,
run reopen, and digest generation.

### 3. Choose The Release Target

Decide whether the next milestone is:

- local-first personal workbench,
- private hosted Streamlit app,
- services-mode deployment,
- or packageable desktop/local workflow.

This decision affects auth, secrets, storage, Notion behavior, and whether
Docker/services parity matters now or later.

### 4. Turn The Provider Matrix Into A Router

The transcription matrix identifies the next provider choices. The next code
step is a tested router with realistic fixtures for diarization, timestamps,
local/private mode, and vocabulary/proper-noun handling.

No runtime default should change until the router has fixtures and a clear
privacy/cost statement.

### 5. Govern The Knowledge Base

The KB is now visible, but it still needs operating discipline: canonical
packs, private-file policy, stale-file review cadence, voice-anchor ownership,
and a migration path for profile metadata.

The product should help agents avoid using stale or sensitive context before
generation starts.

### 6. Add Human-Gated Routing

Handoff drafts and resurfacing digests are intentionally dry-run/report-only.
The next useful step is explicit approval UI or CLI routing for:

- create GitHub issue,
- create/update Linear issue,
- add follow-up queue item,
- publish/send digest,
- save selected output to Notion/markdown.

### 7. Expand SongForge Carefully

SongForge is now a source-linked text pack. Next steps should improve creative
quality while preserving originality and source receipts: optional LLM polish,
more song structures, prompt-pack variants, and export presets.

Do not wire direct music-generation service calls until the text workflow is
useful in real sessions.

## Proposed Next Issue Wave

Create these only after the human decisions in the audit doc are answered:

| ID | Priority | Title | Gate |
| --- | --- | --- | --- |
| `wf-dogfood-loop` | P0 | Run and document a real Wispr Flow-to-output dogfood session | Human supplies real capture/export target |
| `wf-e2e-browser` | P0 | Add end-to-end UI coverage for paste recipe and export loop | Test harness chosen |
| `wf-release-target` | P0 | Decide and implement the next release target | Human chooses local/hosted/services |
| `wf-transcription-router` | P1 | Implement provider router from transcription matrix | Provider/privacy choice confirmed |
| `wf-kb-governance` | P1 | Add KB governance and profile-pack review workflow | Human confirms private/stale policy |
| `wf-handoff-routing` | P1 | Add human-approved GitHub/Linear/follow-up routing | Approval boundary confirmed |
| `wf-digest-automation` | P2 | Add optional resurfacing digest schedule/report flow | Cadence and destination confirmed |
| `wf-songforge-polish` | P2 | Improve SongForge creative quality and exports | Target use case confirmed |

## Audio Repo Consolidation Wave

The canonical repo is `WalksWithASwagger/spektorAI`; the product name remains
WhisperForge. Legacy repos should be archived after README pointers and stale
PR closeout. See
[`docs/AUDIO-REPO-CONSOLIDATION-AUDIT-2026-05-18.md`](docs/AUDIO-REPO-CONSOLIDATION-AUDIT-2026-05-18.md).

| ID | Priority | Title | Source |
| --- | --- | --- | --- |
| `wf-brand-metadata-cleanup` | P0 | Finish public brand, repo metadata, and license decision | `whisperforge`; still needs human license call |
| `wf-watch-folder-inbox` | P1 | Add watch-folder/import-folder capture intake | Shipped in `#37` |
| `wf-knowledge-synthesis` | P1 | Add weekly recaps and topic evolution summaries | Shipped in `#38` |
| `wf-large-file-router-eval` | P1 | Evaluate FFmpeg large-file handling for provider router | Shipped in `#39`; see [`docs/LARGE-FILE-ROUTER-EVALUATION-2026-05-19.md`](docs/LARGE-FILE-ROUTER-EVALUATION-2026-05-19.md) |
| `wf-markdown-vault-export` | P2 | Add Obsidian-friendly markdown vault export | Shipped in `#40` |

## Verification Defaults

- Registry/docs: `python3 -m json.tool ops/roadmap/features.json`, `git diff --check`
- Core Python: `make test`
- Editorial/source receipts: `make eval-fixture`
- Rendered Streamlit shell: `venv/bin/python tests/ui_smoke.py`
- Streamlit health: `make smoke`
- Services mode: `make services-smoke` when Docker/.env are in scope
- Agentic issue readiness:
  `python3 scripts/agentic/issue_lint.py --issue-file issue.md --labels agent:ready`

## Deferred On Purpose

- Generic live dictation overlay behavior already handled well by Wispr Flow
  and peer apps.
- Multi-user auth and database-backed accounts.
- A new frontend framework.
- Provider sprawl without a tested routing matrix.
- Full music generation before the SongForge lyric, structure, and prompt-pack
  workflow proves useful.
