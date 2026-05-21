# WhisperForge Next Round Plan

Last refreshed: 2026-05-21

This is the active workplan for the local-first WhisperForge milestone. Older
dated audit docs remain historical snapshots; use this file, `ROADMAP.md`, and
`STATUS.md` for current direction.

## Current State

WhisperForge is consolidated into `WalksWithASwagger/spektorAI` and the product
name remains WhisperForge.

- Current branch: `main`, synced with `origin/main` before this closeout.
- GitHub issues and PRs: no open items after a live refresh on 2026-05-21.
- Remote branches: only `origin/main`.
- Legacy audio repositories are archived as historical pointers.
- Release target: local-first personal workbench.
- Current verification baseline: `make test` -> `278 passed`, plus lint, JSON,
  rendered UI, browser, fixture, and Streamlit health smokes in normal closeout.
- Latest polish slice: Run Story timeline, Review tab extraction, and
  capture-aware run reopen/review receipts.

## Product Direction

The right next move is not a new architecture. It is making the current loop
feel inevitable:

capture -> recipe -> review -> export -> reopen -> resurface -> handoff.

The product is strongest when it behaves like a local creative operating system
for real voice notes and collaborator follow-through. Keep hosted auth,
multi-user accounts, and direct music-generation service calls deferred until
the local loop feels boringly reliable.

## Prioritized Workplan

| ID | Priority | Title | Why Now |
| --- | --- | --- | --- |
| `wf-demo-fixture-pack` | P0 | Expand the presentation demo fixture pack | Reviewers need a crisp, repeatable demo without live credentials. |
| `wf-review-polish` | P0 | Polish the Review tab for presentation and daily use | Review is now the trust surface; make it legible, calm, and copy-friendly. |
| `wf-kb-governance` | P1 | Add KB governance and profile-pack review workflow | The KB is powerful enough to need explicit stale/private/canonical controls. |
| `wf-router-media-normalization` | P1 | Add fixture-backed media normalization for the transcription router | Large audio/video intake is the next practical extraction bottleneck. |
| `wf-digest-approved-routing` | P1 | Add human-approved routing for resurfacing digests | Resurfacing should become actionable without becoming autonomous spam. |
| `wf-songforge-polish` | P2 | Improve SongForge creative quality and exports | The creative lane is promising, but should mature as text/source workflow first. |

These items are also registered in
[`ops/roadmap/features.json`](../ops/roadmap/features.json) with acceptance
criteria and verification gates.

## Today/Tomorrow Execution Order

1. **Demo fixture pack**
   - Extend `scripts/seed_demo_dataset.py` so the presentation path has one
     strong completed article/handoff run, one SongForge run, and one partial or
     failed run.
   - Update the presentation runbook with exactly which seeded runs to show.
   - Gate with `make browser-e2e` and `make browser-e2e-fresh`.

2. **Review tab polish**
   - Add status-aware Run Story rendering, timestamps where available, and
     compact empty/error states.
   - Add a copy-friendly handoff preview export/download path that works
     without GitHub or Linear credentials.
   - Keep UI tests focused on labels and behavior, not brittle styling.

3. **KB governance**
   - Turn audit warnings into reviewer actions: canonical, ignore, quarantine,
     needs-update.
   - Document the privacy/stale policy for humans and future agents.
   - Surface unresolved governance warnings before generation.

4. **Router media normalization**
   - Convert the provider matrix into fixture-backed FFmpeg/media inspection
     and chunk normalization behavior.
   - Preserve current runtime defaults until privacy/cost receipts are visible.

5. **Digest approved routing**
   - Keep digest generation report-only by default.
   - Add explicit approval for local follow-up queue and Notion draft paths.

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
