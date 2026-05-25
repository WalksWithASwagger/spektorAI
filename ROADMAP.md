# WhisperForge Roadmap

Last reviewed: 2026-05-24

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
  flags, run story timeline, compare/persona variants, and handoff drafts;
- local run workspace with manifests, stage artifacts, reopen, and downstream
  export retry;
- local report-only resurfacing digest;
- text-first SongForge creative pack mode.

## Delivery State

- GitHub issues `#13` through `#24`: closed.
- Audio consolidation issues `#37` through `#40`: closed.
- Pull requests `#25` through `#35` and `#53` through `#56`: merged.
- Latest feature baseline: KB governance, router media planning, approved digest
  routing, and SongForge export polish on current `main`.
- Open GitHub issues: none as of 2026-05-24 (`#49` through `#52` are shipped).
- Open GitHub PRs: none.
- Current unit baseline: `302 passed`.
- Audio repo consolidation audit:
  [`docs/AUDIO-REPO-CONSOLIDATION-AUDIT-2026-05-18.md`](docs/AUDIO-REPO-CONSOLIDATION-AUDIT-2026-05-18.md).
  Next round plan:
  [`docs/NEXT-ROUND-PLAN-2026-05-19.md`](docs/NEXT-ROUND-PLAN-2026-05-19.md).
- Release target decision (owner): local-first personal workbench, recorded in
  issue `#42` and `ops/roadmap/features.json`.

## Roadmap From Here

### 1. Dogfood The Full Loop (Shipped)

Real owner-text capture is now run through capture inbox, recipe selection,
review, markdown/Notion export, run reopen, and resurfacing digest, with
durable artifacts and command outputs recorded in:

[`docs/dogfood/2026-05-20-wispr-flow-loop.md`](docs/dogfood/2026-05-20-wispr-flow-loop.md).

The report produced three concrete friction issues (`#45`-`#47`), and that
closeout wave is now shipped. Use the same dogfood-to-issue pattern to define
the next lane instead of reopening closed items.

### 2. Harden Demo Fixtures And Browser Coverage

The primary browser smokes now cover run-history reopen plus a fresh
paste -> recipe -> review -> export loop. The seeded demo fixture pack now gives
collaborators one strong completed article/handoff run, one SongForge run, and
one partial/error run without live credentials.

Keep browser coverage focused on the same public demo path: paste input, recipe
run, review tab rendering, markdown export, run reopen, and digest generation.

### 3. Execute The Local-First Milestone

The current milestone target is local-first personal workbench. Immediate scope
is fast local capture -> recipe -> review -> export loops with explicit
human-gated routing controls.

Deferred until later milestone:

- hosted auth/multi-user accounts,
- services-mode parity beyond current stability baseline,
- deployment hardening for public/private hosted surfaces.

### 4. Turn The Provider Matrix Into A Router (Shipped Slice + Next)

The transcription matrix now has fixture-backed media inspection, FFmpeg
normalization planning, and privacy/cost receipts. The next code step is
runtime validation and transcript assembly before changing defaults.

No runtime default should change until the router has fixtures and a clear
privacy/cost statement.

### 5. Govern The Knowledge Base (Shipped Slice + Next)

The KB now has reviewer actions, canonical/ignored governance marks, and
generation warnings for unresolved findings. The next operating step is real
reviewer cleanup of stale/private-looking profile files.

The product should help agents avoid using stale or sensitive context before
generation starts.

### 6. Expand Human-Gated Routing (Shipped Slice + Next)

Handoff drafts now support explicit approval to create GitHub/Linear issues and
append to a local follow-up queue with dry-run defaults and an env kill switch.
The next useful step is expanding that approval boundary to:

- publish/send digest,
- create/update Notion task pages.

### 7. Expand SongForge Carefully (Shipped Slice + Next)

SongForge now emits multiple source-linked structure variants with originality
guardrails and markdown/vault export coverage. Next steps should come from
real-session creative feedback.

Do not wire direct music-generation service calls until the text workflow is
useful in real sessions.

## Most Recent Shipped Issue Wave (2026-05)

As of 2026-05-24 there is no active open GitHub implementation wave. This table
tracks the latest shipped slice for traceability.

| ID | Priority | Title | Gate |
| --- | --- | --- | --- |
| `wf-digest-signal-filter` | P0 | Filter digest signal so real captures are not drowned by smoke/demo artifacts | Shipped in `#45` |
| `wf-run-capture-status-sync` | P0 | Sync run-manifest capture metadata with final capture status | Shipped in `#46` |
| `wf-export-readiness-refresh` | P0 | Refresh scorecard/handoff readiness signals after export events | Shipped in `#47` |
| `wf-transcription-router` | P1 | Implement provider router from transcription matrix | Shipped in `#48` |
| `wf-demo-fixture-pack` | P0 | Expand the presentation demo fixture pack | Shipped; browser smokes stay credential-free |
| `wf-review-polish` | P0 | Polish the Review tab for presentation and daily use | Shipped; rendered UI smoke covers labels/behavior |
| `wf-kb-governance` | P1 | [#49](https://github.com/WalksWithASwagger/spektorAI/issues/49) Add KB governance and profile-pack review workflow | Shipped in `#53` |
| `wf-router-media-normalization` | P1 | [#50](https://github.com/WalksWithASwagger/spektorAI/issues/50) Add fixture-backed media normalization for the transcription router | Shipped in `#54`; runtime defaults preserved |
| `wf-digest-approved-routing` | P1 | [#51](https://github.com/WalksWithASwagger/spektorAI/issues/51) Add human-approved routing for resurfacing digests | Shipped in `#55`; explicit approval remains required |
| `wf-songforge-polish` | P2 | [#52](https://github.com/WalksWithASwagger/spektorAI/issues/52) Improve SongForge creative quality and exports | Shipped in `#56` |

## Audio Repo Consolidation Wave

The canonical repo is `WalksWithASwagger/spektorAI`; the product name remains
WhisperForge. Legacy repos should be archived after README pointers and stale
PR closeout. See
[`docs/AUDIO-REPO-CONSOLIDATION-AUDIT-2026-05-18.md`](docs/AUDIO-REPO-CONSOLIDATION-AUDIT-2026-05-18.md).

| ID | Priority | Title | Source |
| --- | --- | --- | --- |
| `wf-brand-metadata-cleanup` | P0 | Finish public brand, repo metadata, and license decision | Shipped in `#36`; no license file added |
| `wf-watch-folder-inbox` | P1 | Add watch-folder/import-folder capture intake | Shipped in `#37` |
| `wf-knowledge-synthesis` | P1 | Add weekly recaps and topic evolution summaries | Shipped in `#38` |
| `wf-large-file-router-eval` | P1 | Evaluate FFmpeg large-file handling for provider router | Shipped in `#39`; see [`docs/LARGE-FILE-ROUTER-EVALUATION-2026-05-19.md`](docs/LARGE-FILE-ROUTER-EVALUATION-2026-05-19.md) |
| `wf-markdown-vault-export` | P2 | Add Obsidian-friendly markdown vault export | Shipped in `#40` |

## Verification Defaults

- Registry/docs: `python3 -m json.tool ops/roadmap/features.json`, `git diff --check`
- Syntax/high-signal static rail: `make lint`
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
