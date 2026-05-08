# WhisperForge Roadmap

Last reviewed: 2026-05-07

This roadmap is based on the current repository structure, documentation,
unit tests, smoke test, and the recent refactor history. It favors surgical
stabilization over new architecture: the direct Streamlit monolith is the
working product surface; microservices mode should be brought back to parity
only where it helps deployment or isolation.

## Current State

WhisperForge is now a single-user content production workbench:

- `app.py` is a thin Streamlit composition root.
- `ui/` owns session state, dialogs, input, pipeline display, output, sidebar,
  and shell chrome.
- `whisperforge_core/` owns transcription, LLM calls, prompts, Notion export,
  markdown export, cost/history, images, pipeline orchestration, cache, and RAG.
- `services/` wraps selected core behavior with FastAPI for docker-compose mode.
- `prompts/` holds user profiles, prompt overrides, and knowledge bases.
- `patterns/` holds a large local prompt-pattern corpus.
- `tests/` has a meaningful unit suite covering cost, cache, export, history,
  prompts, audio, Notion rendering, agentic pipeline behavior, and RAG.

Verified on this pass:

- `venv/bin/python -m pytest tests/ -q` passes: 148 tests.
- `tests/smoke.sh` passes when allowed to bind localhost port `8599`.
- The root docs are mostly current, but still contain stale test-count and
  layout details.
- The repo still has 33 tracked files under `whisperforge-env/`, despite
  `.gitignore` now excluding that environment.

## Product Direction

The strongest product path is not "more knobs." It is:

1. Make the local monolith boringly reliable.
2. Preserve the visual identity and fast daily workflow.
3. Make every run recoverable, inspectable, and exportable.
4. Use benchmark-driven KB/RAG decisions instead of guessing.
5. Turn voice/persona/profile management into a first-class creative system.
6. Only then harden containerized services and external deployment.

## Roadmap

### Phase 0: Repo And Documentation Hygiene

Goal: make the project restartable by any future session without archaeology.

Success criteria:

- `readme.md`, `changelog.md`, and this roadmap agree on current capabilities.
- The root docs clearly distinguish direct mode from services mode.
- No virtualenv, cache, or generated artifacts are tracked.
- A short `STATUS.md` exists with the latest verified commands and known risks.

Work:

- Update README test count and pipeline description to match the current
  148-test suite and newer output features.
- Add a compact root `STATUS.md` after each meaningful work session.
- Remove tracked `whisperforge-env/` files from git while keeping local envs
  ignored.
- Document the tested Python version matrix and the recommended venv name.
- Add a "known service-mode gaps" section so docs do not overpromise.

### Phase 1: Stabilize The Daily Local App

Goal: the Streamlit app should be safe to use for real content without
session-state surprises or hidden data loss.

Success criteria:

- Smoke test stays green.
- A small browser/UI verification checklist exists for the main flows.
- A failed Notion save, image generation call, or LLM call does not erase the
  run output.
- Auto-save, markdown export, history, and run metrics behave consistently.

Work:

- Add a local runtime verification script beyond healthcheck: load app, render
  sidebar/settings/output shells, and assert no frontend exception text.
- Add focused tests for run-metrics assembly and auto-export behavior around
  `_build_bundle`.
- Make the save/export path idempotent enough to retry without duplicating
  local markdown filenames or corrupting history.
- Review session-state defaults for mutable values and hidden widget-key drift.
- Keep the visual treatment in `styles.py`, but document the key selectors that
  must survive Streamlit upgrades.

### Phase 2: Bring Services Mode To Feature Parity

Goal: docker-compose mode should either match direct mode or be explicitly
scoped as legacy/minimal.

Success criteria:

- `HttpProcessor.run_pipeline()` accepts every option that
  `LocalProcessor.run_pipeline()` accepts.
- Processing service schemas carry cleanup, chapters, segments, images, article
  length, RAG mode, compare model, personas, and fact-check options.
- Storage service can save the full modern `ContentBundle`, including chapters,
  cleaned transcript, critique, fact-check flags, generated images, compare,
  personas, markdown/export metadata, and run metrics.
- Transcription service can return detailed segments when the backend supports
  them.
- docker-compose smoke test verifies all service health endpoints and one
  minimal end-to-end text pipeline request.

Work:

- Expand Pydantic request/response models in `services/processing/service.py`.
- Expand `whisperforge_core/http_adapters.py` to round-trip the full
  `PipelineResult`.
- Expand `services/storage/service.py` and `HttpStorage.save()` to preserve all
  Notion/export fields.
- Add tests that compare direct and HTTP adapter payload shapes.
- Keep the implementation thin: wrappers should call `whisperforge_core`, not
  fork business logic.

### Phase 3: Make Runs Recoverable

Goal: long content runs should survive interruptions and be easy to inspect.

Success criteria:

- Every run has a stable local run ID.
- Intermediate stage outputs are checkpointed.
- The user can resume or export a partial run.
- Cost, token, cache, model, settings, and source metadata are attached to the
  run record before Notion save.

Work:

- Introduce a `RunRecord` or equivalent plain data model in core.
- Write stage outputs to `.cache/runs/<run_id>/` as the pipeline progresses.
- Replace scattered session-only state with session state plus recoverable run
  files.
- Add retry buttons for Notion save, markdown export, and image generation.
- Make history records link to local run artifacts as well as Notion URLs.

### Phase 4: Upgrade Voice, Profiles, And Knowledge Base

Goal: the user's voice system becomes a deliberate asset, not just a folder of
files.

Success criteria:

- Profiles can define prompts, knowledge-base docs, personas, and style
  settings in one discoverable structure.
- Built-in personas and user-defined personas share one loading path.
- RAG default behavior is explained and measurable from the UI.
- Sensitive/private profile files are clearly separated from distributable
  defaults.

Work:

- Add `prompts/<user>/profile.yaml` for defaults such as provider, model,
  style, personas, RAG mode, and Notion target.
- Implement user persona discovery under `prompts/<user>/personas/*.md`.
- Add a profile audit dialog: missing prompts, KB size, RAG benchmark summary,
  private file warning, and stale profile settings.
- Promote the KB benchmark into a preflight recommendation: Auto can explain
  why it chose legacy or RAG for the current profile.
- Split sample/default prompts from private working profiles if this repo will
  ever be shared.

### Phase 5: Improve Editorial Quality And Grounding

Goal: output should feel less like a pipeline and more like an editor that
knows the source.

Success criteria:

- Article drafts cite or quote source moments where useful.
- Fact-check output is actionable and visible before save.
- Persona and compare outputs can be judged quickly.
- A small evaluation set catches regressions in voice, grounding, and length.

Work:

- Add a local `evals/` fixture set with representative transcripts and expected
  qualitative checks.
- Add structured critique categories and expose them in the UI.
- Add "source receipts": transcript quotes or chapter references beside key
  claims in long-form outputs.
- Add side-by-side compare scoring for selected providers/personas.
- Tune article length behavior with tests around max token budgets and observed
  word counts from fixture outputs.

### Phase 6: Deployment And Operations

Goal: deployment is a choice, not a science project.

Success criteria:

- A clean machine can bootstrap the repo from documented commands.
- Secrets are documented by deployment mode.
- Direct mode, services mode, and fully-local mode each have a tested runbook.
- CI runs unit tests and a lightweight smoke test.

Work:

- Add `Makefile` or `justfile` commands for setup, test, smoke, run, services,
  and clean.
- Add GitHub Actions for tests, lint/import checks, and smoke where feasible.
- Add docker-compose end-to-end smoke for service mode.
- Document model/provider availability checks and fallback behavior.
- Decide whether microservices are truly needed for production; if not, remove
  or archive them after the parity decision.

## Near-Term Backlog

P0:

- Fix stale README test count and feature details.
- Stop tracking `whisperforge-env/`.
- Add `STATUS.md` with verified commands and current risks.
- Document services-mode parity gaps.

P1:

- Add browser-level Streamlit verification.
- Add direct-vs-services payload parity tests.
- Expand HTTP/service schemas for modern pipeline options.
- Add run checkpointing for save/export retry.

P2:

- Add profile manifests.
- Add user-defined persona discovery.
- Add source receipts and a small editorial eval fixture set.
- Add CI once local commands are stable.

## Deferred On Purpose

- Multi-user auth and database-backed accounts.
- A new frontend framework.
- A new orchestration framework for the pipeline.
- Provider sprawl before existing OpenAI, Anthropic, Ollama, and image lanes
  are verified.
- Large cleanup of the `patterns/` corpus before deciding whether it is product
  data, profile data, or archival material.

## Decision Log

- Direct mode is the primary product surface until services mode reaches parity.
- RAG is a measured optimization, not a default ideology. Keep benchmark-first
  behavior.
- The visual identity is part of the product. Refactors should preserve the
  gradient, motion, and control-center feel unless intentionally redesigned.
- Documentation should describe verified behavior, not planned behavior.
