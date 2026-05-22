# WhisperForge Next Round Plan

Last refreshed: 2026-05-22

This is the active workplan for the local-first WhisperForge milestone. Older
dated audit docs remain historical snapshots; use this file, `ROADMAP.md`, and
`STATUS.md` for current direction.

## Current State

WhisperForge is consolidated into `WalksWithASwagger/spektorAI` and the product
name remains WhisperForge.

- Current branch: `main`, synced with `origin/main` after merging the issue
  swarm.
- GitHub issues: no open issues after `#49` through `#52` were closed by
  merged PRs `#53` through `#56`. No open PRs.
- Remote branches: only `origin/main`.
- Legacy audio repositories are archived as historical pointers.
- Release target: local-first personal workbench.
- Current verification baseline: `make test` -> `301 passed`, plus `make lint`,
  `make eval-fixture`, `make digest`, and `git diff --check` in closeout.
- Latest shipped slice: KB governance controls, router media planning,
  approved digest routing, and SongForge structure/export polish.

## Product Direction

The right next move is not a new architecture. It is making the current loop
feel inevitable:

capture -> recipe -> review -> export -> reopen -> resurface -> handoff.

The product is strongest when it behaves like a local creative operating system
for real voice notes and collaborator follow-through. Keep hosted auth,
multi-user accounts, and direct music-generation service calls deferred until
the local loop feels boringly reliable.

## Shipped Workplan

| ID | Issue | Priority | Title | Why Now |
| --- | --- | --- | --- | --- |
| `wf-kb-governance` | [#49](https://github.com/WalksWithASwagger/spektorAI/issues/49) / [#53](https://github.com/WalksWithASwagger/spektorAI/pull/53) | P1 | Add KB governance and profile-pack review workflow | Shipped canonical/ignored KB controls, reviewer actions, warnings, docs, and tests. |
| `wf-router-media-normalization` | [#50](https://github.com/WalksWithASwagger/spektorAI/issues/50) / [#54](https://github.com/WalksWithASwagger/spektorAI/pull/54) | P1 | Add fixture-backed media normalization for the transcription router | Shipped opt-in ffprobe planning, planned-only FFmpeg normalization, and privacy/cost receipts. |
| `wf-digest-approved-routing` | [#51](https://github.com/WalksWithASwagger/spektorAI/issues/51) / [#55](https://github.com/WalksWithASwagger/spektorAI/pull/55) | P1 | Add human-approved routing for resurfacing digests | Shipped explicit approval gates, local follow-up queue routing, and Notion draft routing. |
| `wf-songforge-polish` | [#52](https://github.com/WalksWithASwagger/spektorAI/issues/52) / [#56](https://github.com/WalksWithASwagger/spektorAI/pull/56) | P2 | Improve SongForge creative quality and exports | Shipped structure variants, originality guardrails, fixture evals, and export preservation. |

These items are also registered in
[`ops/roadmap/features.json`](../ops/roadmap/features.json) with acceptance
criteria and verification gates.

## Next Execution Order

1. Dogfood the merged local-first loop with a real capture and record the
   resulting friction.
2. Turn that evidence into the next issue wave instead of reopening the closed
   `#49` through `#52` items.
3. Keep runtime defaults conservative until router privacy/cost receipts and
   approved routing paths have real-session review.

## Human Decisions Needed

- What should count as canonical profile context: only curated files, or any KB
  file not flagged as stale/private?
- Should presentation reviewers see Notion export live, or should the default
  demo stay local markdown/vault-only?
- For router work, is the first real priority long audio, video extraction,
  speaker diarization, or private/local transcription?
- Should digest routing create tasks, pages, or queue items first?

## Not Yet

- Do not add new transcription providers before router fixtures exist.
- Do not automate digest publication without an explicit approval boundary.
- Do not build hosted/multi-user auth until the local-first milestone is stable.
- Do not expand SongForge into direct music-generation service calls before the
  text workflow has real-session feedback.
