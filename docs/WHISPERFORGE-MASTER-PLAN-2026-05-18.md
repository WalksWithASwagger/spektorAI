# WhisperForge Master Plan

Date: 2026-05-18

## Delivery Status

The implementation wave seeded from this plan has shipped. GitHub issues
`#13` through `#24` are closed, PRs `#25` through `#35` are merged, and the
current from-here audit lives in
[`docs/WHISPERFORGE-AUDIT-AND-ROADMAP-2026-05-18.md`](WHISPERFORGE-AUDIT-AND-ROADMAP-2026-05-18.md).

This plan resets WhisperForge around the current voice-product landscape and
the repo's now-large KK knowledge base. It assumes Wispr Flow remains the
primary live dictation layer. WhisperForge should become the place where
spoken thinking is grounded, shaped, evaluated, published, resurfaced, and,
when useful, turned into creative artifacts.

## North Star

WhisperForge turns raw spoken thought into source-grounded, publishable,
agent-ready output in KK's voice.

The product should feel like a voice-to-knowledge forge:

1. Capture the thought.
2. Ground it in the profile, knowledge base, transcript, and prior work.
3. Compose useful artifacts with receipts.
4. Hand work to Notion, markdown, GitHub, Linear, or follow-up queues.
5. Preserve runs so nothing disappears.
6. Surface the best material later.
7. Offer a creative lane for lyrics, spoken-word scripts, and song prompt
   packs when the source material wants to perform.

## What Changed In The Market

The old product premise was "transcribe audio and make content." The current
market has moved past raw transcription. The live edge is now a stack:

- ambient dictation into any app,
- context-aware cleanup and vocabulary,
- team dictionaries and snippets,
- local or privacy-controlled speech processing,
- source-grounded notebooks,
- agent voice loops,
- and reusable workflows/prompt modes.

Useful signals from the 2026 scan:

- Wispr Flow is now a strong live dictation baseline, with personal dictionary,
  snippets, app-specific styles, team dictionaries, usage dashboards, developer
  syntax handling, and file tagging for coding tools. Its help docs also make
  context awareness explicit, including nearby text, proper nouns, app metadata,
  dictionary entries, and coding-context names during active dictation.
- Superwhisper's strongest product idea is not just transcription; it is
  custom modes that combine dictated text, application context, selected text,
  clipboard context, and user-defined AI instructions. Its privacy docs frame
  speech-to-text and post-processing as separately configurable stages.
- Aqua Voice's useful lesson is intent-first dictation. Its guide says it works
  in any text box and adapts output to the destination. Its YC launch framed
  the product as dictation that understands intent rather than requiring rigid
  commands.
- VoiceInk and other local-first tools keep pushing the privacy baseline:
  offline Whisper, no cloud for the free tier, custom vocabulary, and optional
  cloud real-time transcription.
- NotebookLM proves that source-grounded knowledge products now need citations,
  source upload breadth, audio/source summaries, and interactive follow-up.
- Spokenly's MCP docs show a near-future pattern where agents can ask humans
  questions by voice and continue with the answer as structured context.
- OpenAI, Deepgram, and AssemblyAI all signal that modern speech-to-text is
  improving around proper nouns, noisy speech, multilingual use, streaming,
  vocabulary adaptation, formatting, and hallucination reduction.

Implication: WhisperForge should not chase Wispr Flow as a general dictation
overlay. It should integrate with whatever the user dictates elsewhere, then
win at durable knowledge work, editorial quality, receipts, and agent handoff.

## Product Position

### Do

- Treat Wispr Flow, audio upload, pasted transcripts, and future voice tools as
  capture inputs.
- Make the KK knowledge base inspectable, searchable, scored, and useful.
- Turn one voice capture into many output types: article, brief, social,
  source receipts, follow-up tasks, issue drafts, song materials, and Notion
  pages.
- Preserve run artifacts and let the user reopen, resume, compare, and export.
- Make grounding visible enough that the user can trust what shipped.
- Keep local/privacy modes clear without pretending every mode is private.

### Do Not

- Build a generic live dictation clone.
- Add provider sprawl without an explicit selection model and eval gate.
- Hide source material behind a "trust me" draft.
- Let the knowledge base become a silent prompt dump with stale files.
- Turn SongForge into an unbounded music-generation platform before the lyric,
  structure, and prompt-pack workflow is useful.

## System Model

WhisperForge should organize work around five durable objects:

1. Capture
   Raw audio, pasted transcript, Wispr Flow text, source URL, or imported note.

2. Knowledge
   Profile docs, voice guides, style guides, project context, source packs,
   prior outputs, and stale-signal reports.

3. Recipe
   A repeatable command such as "article with receipts," "LinkedIn carousel
   notes," "GitHub issue batch," "client brief," or "song prompt pack."

4. Run
   Inputs, settings, checkpoints, outputs, costs, receipts, evaluation scores,
   and export targets.

5. Handoff
   Notion page, markdown export, GitHub issue, Linear issue, follow-up queue,
   social draft, or creative prompt pack.

## Roadmap

### Phase 1: Voice Inbox And Capture Handoff

Build a central inbox for incoming thought. The user should be able to paste a
Wispr Flow dictation, upload audio, import a transcript, or save a raw note,
then decide what recipe to run.

Key outcomes:

- one capture list with source type, created time, title, status, and run links,
- quick paste/import path for Wispr Flow output,
- transcript/audio normalization before pipeline execution,
- capture metadata that follows the run into Notion/markdown.

### Phase 2: Knowledge Base Intelligence

Make the KK knowledge base a visible asset instead of a folder. The app should
show what docs exist, what they are for, when they last changed, how often they
are retrieved, and where stale or conflicting guidance may confuse output.

Key outcomes:

- KB inventory and health report,
- stale/duplicate/private-file warnings,
- source catalog for profile docs and project docs,
- retrieval inspector that explains why a chunk was used.

### Phase 3: Recipe And Command System

Replace scattered controls with reusable recipes. A recipe should declare
inputs, model/provider defaults, KB mode, output sections, eval checks, and
handoff targets.

Key outcomes:

- recipe files or manifests under profile/project scope,
- command palette UI,
- recipe-level verification expectations,
- a way to run and compare recipes without changing code.

### Phase 4: Source-Grounded Composition Studio

Turn output review into a serious editor. The user should see article/social/
brief outputs alongside source receipts, claim flags, quotes, and revision
notes.

Key outcomes:

- evidence panel next to drafted content,
- claim/source receipts for article and brief outputs,
- compare/persona variants with visible scoring,
- export that keeps evidence with the artifact.

### Phase 5: Modern Speech And Privacy Matrix

Keep transcription current without letting it become the whole product. The
app should make it clear when it is using OpenAI, local Whisper/MLX, WhisperX,
Deepgram, AssemblyAI, or another backend, and what tradeoffs that implies.

Key outcomes:

- provider/router matrix for accuracy, streaming, timestamps, diarization,
  local/offline, custom vocabulary, cost, and privacy,
- current defaults documented in UI and docs,
- eval fixtures that catch transcript quality regressions.

### Phase 6: Evaluation And Trust

Create scorecards that make quality visible. The app should answer: did this
sound like KK, did it stay grounded, is it useful, and did it obey the recipe?

Key outcomes:

- voice score,
- grounding score,
- usefulness/ready-to-publish score,
- fixture eval set for recurring regression checks,
- compact run-level verdict in history/export.

### Phase 7: Agentic Handoffs And Resurfacing

WhisperForge should be able to turn a capture into work for agents, not just
content for a reader.

Key outcomes:

- GitHub/Linear issue drafts from a capture or plan,
- follow-up queues for unresolved ideas,
- Notion/markdown/social handoffs with source links,
- resurfacing digest that keeps good material from disappearing.

### Phase 8: Recovery And Run Workspace

The pipeline now writes run artifacts. The product should expose them as a
workspace: reopen, resume, re-export, compare, and retry failed stages.

Key outcomes:

- run browser with local artifact links,
- reopen/resume from manifest,
- retry selected stage or handoff,
- export bundle with settings, receipts, and eval summary.

### Phase 9: SongForge Creative Lane

The "maybe we turn this into a song" path should become a bounded creative
mode. It should transform a transcript or KB cluster into song-ready materials,
not claim to be a full music studio yet.

Key outcomes:

- lyrical theme extraction,
- chorus/verse/bridge structure drafts,
- spoken-word and song lyric variants,
- Suno/Udio-style prompt packs without hardcoding any one service,
- source notes that explain where lines/themes came from.

## Issue Wave

These are the implementation-sized units to seed into GitHub and Linear.

| ID | Priority | GitHub | Linear | Title | Phase |
| --- | --- | --- | --- | --- | --- |
| `wf-voice-inbox` | P0 | [#13](https://github.com/WalksWithASwagger/spektorAI/issues/13) | [BC-221](https://linear.app/bc-ai/issue/BC-221/build-wispr-flow-voice-inbox-and-capture-handoff) | Build Wispr Flow voice inbox and capture handoff | Phase 1 |
| `wf-kb-inventory` | P0 | [#14](https://github.com/WalksWithASwagger/spektorAI/issues/14) | [BC-222](https://linear.app/bc-ai/issue/BC-222/add-knowledge-base-inventory-and-health-audit) | Add knowledge-base inventory and health audit | Phase 2 |
| `wf-retrieval-inspector` | P0 | [#15](https://github.com/WalksWithASwagger/spektorAI/issues/15) | [BC-223](https://linear.app/bc-ai/issue/BC-223/add-source-grounded-retrieval-inspector) | Add source-grounded retrieval inspector | Phase 2 |
| `wf-recipe-system` | P1 | [#16](https://github.com/WalksWithASwagger/spektorAI/issues/16) | [BC-224](https://linear.app/bc-ai/issue/BC-224/add-prompt-recipe-manifests-and-command-palette) | Add prompt recipe manifests and command palette | Phase 3 |
| `wf-compose-studio` | P1 | [#17](https://github.com/WalksWithASwagger/spektorAI/issues/17) | [BC-226](https://linear.app/bc-ai/issue/BC-226/build-source-grounded-composition-studio) | Build source-grounded composition studio | Phase 4 |
| `wf-transcription-matrix` | P1 | [#18](https://github.com/WalksWithASwagger/spektorAI/issues/18) | [BC-225](https://linear.app/bc-ai/issue/BC-225/add-modern-transcription-provider-and-privacy-matrix) | Add modern transcription provider and privacy matrix | Phase 5 |
| `wf-eval-scorecards` | P1 | [#19](https://github.com/WalksWithASwagger/spektorAI/issues/19) | [BC-227](https://linear.app/bc-ai/issue/BC-227/add-voice-grounding-and-usefulness-scorecards) | Add voice, grounding, and usefulness scorecards | Phase 6 |
| `wf-agent-handoffs` | P1 | [#20](https://github.com/WalksWithASwagger/spektorAI/issues/20) | [BC-228](https://linear.app/bc-ai/issue/BC-228/create-agentic-handoff-exports-for-issues-and-follow-ups) | Create agentic handoff exports for issues and follow-ups | Phase 7 |
| `wf-run-workspace` | P1 | [#21](https://github.com/WalksWithASwagger/spektorAI/issues/21) | [BC-229](https://linear.app/bc-ai/issue/BC-229/add-run-artifact-reopen-resume-and-retry-ui) | Add run artifact reopen, resume, and retry UI | Phase 8 |
| `wf-profile-os` | P2 | [#22](https://github.com/WalksWithASwagger/spektorAI/issues/22) | [BC-230](https://linear.app/bc-ai/issue/BC-230/upgrade-profiles-into-a-voiceproject-operating-system) | Upgrade profiles into a voice/project operating system | Phase 2 |
| `wf-resurfacing-digest` | P2 | [#23](https://github.com/WalksWithASwagger/spektorAI/issues/23) | [BC-231](https://linear.app/bc-ai/issue/BC-231/add-resurfacing-digest-for-captures-and-generated-outputs) | Add resurfacing digest for captures and generated outputs | Phase 7 |
| `wf-songforge` | P2 | [#24](https://github.com/WalksWithASwagger/spektorAI/issues/24) | [BC-232](https://linear.app/bc-ai/issue/BC-232/prototype-songforge-lyric-and-prompt-pack-mode) | Prototype SongForge lyric and prompt-pack mode | Phase 9 |

## Verification Strategy

Use the smallest proof that matches each change:

- Docs/registry changes: `python3 -m json.tool ops/roadmap/features.json` and
  `git diff --check`.
- Core Python changes: `make test`.
- Rendered UI changes: `venv/bin/python tests/ui_smoke.py`.
- Streamlit health: `make smoke`.
- Editorial/receipt changes: `make eval-fixture`.
- Services work: `make services-smoke` or a documented local equivalent.
- Agentic issue readiness: `python3 scripts/agentic/issue_lint.py` against the
  proposed issue body with `agent:ready`.

## Research Sources

- Wispr Flow features: https://wisprflow.ai/features
- Wispr Flow context awareness: https://docs.wisprflow.ai/articles/4678293671-feature-context-awareness
- Wispr Flow overview: https://docs.wisprflow.ai/articles/2772472373-what-is-flow
- Superwhisper custom modes: https://superwhisper.com/docs/modes/custom
- Superwhisper sensitive-data controls: https://superwhisper.com/docs/security/sensitive-data
- Aqua Voice user guide: https://aquavoice.com/guide/index
- Aqua Voice YC launch: https://www.ycombinator.com/launches/Kjl-aqua-voice-voice-only-text-editor
- VoiceInk local dictation: https://www.voice-ink.com/
- NotebookLM overview: https://support.google.com/notebooklm/answer/16164461?hl=en
- NotebookLM Audio Overview: https://support.google.com/notebooklm/answer/16212820?hl=en
- Spokenly voice-for-agents MCP: https://spokenly.app/docs/macos/voice-for-agents
- Spokenly agent mode: https://spokenly.app/docs/macos/agent-mode
- OpenAI next-generation audio models: https://openai.com/index/introducing-our-next-generation-audio-models/
- Deepgram model overview: https://developers.deepgram.com/docs/models-languages-overview
- AssemblyAI Universal-2 overview: https://support.assemblyai.com/articles/4814967928-what-is-conformer-2
