# WhisperForge Roadmap

Last reviewed: 2026-05-18

This roadmap now points at the 2026 product reset rather than trying to hold
every detail inline. The master plan is
[`docs/WHISPERFORGE-MASTER-PLAN-2026-05-18.md`](docs/WHISPERFORGE-MASTER-PLAN-2026-05-18.md).

## Current State

WhisperForge is a single-user voice-to-content workbench with a direct
Streamlit app, shared Python core, optional FastAPI services mode, local run
artifacts, source receipts, profile manifests, RAG benchmarking, and an
agentic GitHub/Linear delivery loop.

Verified baseline before this planning branch:

- Branch: `main`, synced with `origin/main`.
- Commit: `e607252 feat: add agentic delivery contract`.
- GitHub repo: `WalksWithASwagger/spektorAI`.
- Open GitHub issues/PRs before this wave: none.
- Linear project: [WhisperForge Roadmap](https://linear.app/bc-ai/project/whisperforge-roadmap-317805524537).
- Previous Linear wave `BC-57`, `BC-58`, `BC-63`, `BC-73`, `BC-83`,
  `BC-88`, `BC-90`, and `BC-91`: Done.
- Previous verification: `make test` passed with 192 tests, plus
  `make eval-fixture`, `make smoke`, `venv/bin/python tests/ui_smoke.py`,
  `python3 -m json.tool ops/roadmap/features.json`, and `git diff --check`.

## Product Direction

The product should not clone Wispr Flow. Wispr Flow is already a strong live
dictation layer. WhisperForge should sit after capture and win at durable
knowledge work:

1. Capture spoken thought from audio, pasted transcripts, Wispr Flow output,
   and imported notes.
2. Ground work in the KK knowledge base, profile docs, source packs, and prior
   outputs.
3. Compose articles, briefs, social drafts, source receipts, follow-ups,
   issue drafts, and creative prompt packs.
4. Preserve runs so outputs, settings, receipts, and costs can be reopened.
5. Resurface the best material so the knowledge base does not trap signal.

## Phases

### Phase 1: Voice Inbox And Capture Handoff

Build a central capture inbox for Wispr Flow text, pasted notes, uploaded
audio, imported transcripts, and future voice tools.

### Phase 2: Knowledge Base Intelligence

Make profile and knowledge-base files inspectable, searchable, scored, and
auditable. Add stale, duplicate, and privacy warnings before the KB confuses
generation.

### Phase 3: Recipe And Command System

Move repeated workflows into recipe manifests and a command palette so the app
can run "article with receipts," "client brief," "issue wave," or
"SongForge prompt pack" without new code.

### Phase 4: Source-Grounded Composition Studio

Show drafted output beside evidence, quotes, claim flags, compare/persona
variants, and revision notes.

### Phase 5: Modern Speech And Privacy Matrix

Keep transcription current with a clear provider/router matrix for cloud,
local, streaming, timestamps, diarization, vocabulary, cost, and privacy.

### Phase 6: Evaluation And Trust

Add voice, grounding, usefulness, and recipe-compliance scorecards that can run
against fixtures and recent outputs.

### Phase 7: Agentic Handoffs And Resurfacing

Turn captures and plans into GitHub/Linear issues, Notion/markdown/social
handoffs, follow-up queues, and periodic resurfacing digests.

### Phase 8: Recovery And Run Workspace

Expose local run artifacts as a user-facing workspace: reopen, resume, retry,
compare, and export.

### Phase 9: SongForge Creative Lane

Prototype a bounded lyric/spoken-word/prompt-pack mode that turns transcripts
and KB clusters into song-ready materials without pretending to be a full
music studio.

## Active Issue Wave

The next wave is tracked in
[`ops/roadmap/features.json`](ops/roadmap/features.json). Implementation issues
should keep the agentic issue shape required by
[`docs/AGENTIC-DELIVERY.md`](docs/AGENTIC-DELIVERY.md):

- `## Context`
- `## Acceptance Criteria`
- `## Tests/Evals`
- `## Verification`
- `## Agent Instructions`
- `## Out of Scope`

## Verification Defaults

- Docs/registry: `python3 -m json.tool ops/roadmap/features.json` and
  `git diff --check`
- Python/core: `make test`
- Streamlit shell: `venv/bin/python tests/ui_smoke.py`
- Health smoke: `make smoke`
- Editorial/source receipts: `make eval-fixture`
- Services mode: `make services-smoke` or a documented local equivalent
- Agentic issue lint: `python3 scripts/agentic/issue_lint.py --issue-file issue.md --labels agent:ready`

## Deferred On Purpose

- Generic live dictation overlay behavior already handled well by Wispr Flow
  and peer apps.
- Multi-user auth and database-backed accounts.
- A new frontend framework.
- Provider sprawl without a tested routing matrix.
- Full music generation before the SongForge lyric, structure, and prompt-pack
  workflow proves useful.
