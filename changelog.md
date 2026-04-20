# WhisperForge Changelog

All notable changes to WhisperForge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.0] - 2026-04-19

### Added
- **RAG on knowledge base** — new `whisperforge_core/rag/` package. When a user's KB grows past 25 chunks (or `WF_RAG=1` / KB mode = "Always" in the UI), the pipeline switches from dumping the whole KB on every call to per-stage top-K retrieval with an always-included voice anchor.
  - `chunker.py` — heading-aware split (top-3 markdown levels) with sliding-window fallback for oversized sections and .txt docs.
  - `embedder.py` — lazy `sentence-transformers/all-MiniLM-L6-v2` (cached, MPS-accelerated on Apple Silicon). Override via `WF_EMBED_MODEL`.
  - `store.py` — numpy cosine + on-disk persistence at `.cache/rag/<user>/<embed_hash>/` with mtime-based invalidation.
  - `retriever.py` — stage-specific query augmentation map, voice-anchor heuristic (filename match on voice/style/tone/writing/persona), block rendering.
- **KB mode** segmented control in ⚙ Generation Settings: Auto / Always / Never.
- Live verified: wisdom stage dropped from ~6000 → ~2300 input tokens (62%) with RAG engaged on KK's KB. Auto mode keeps small KBs on the legacy "dump + cache" path since prompt caching already wins there.

### Dependencies
- `sentence-transformers>=2.7,<6` — pinned below v6 because v6 adds a hard torchcodec dep that breaks on macOS without exact FFmpeg libavutil versions.

## [0.7.0] - 2026-04-19

### Added
- **Auto-save to Notion** at end of pipeline (default ON, opt-out via ⚙ Generation Settings). Restores the old Record-tab "I'm Feeling Lucky" auto-save behavior as a flag. Lazy-imports `ui.output._save_to_notion` from `ui.pipeline` to avoid circular dependency. `st.toast` confirms or warns.
- **Article length targeting** — segmented control (Brief / Standard / Long-form) maps to ~500 / 1500 / 3000 words. Routed into both `article_writing` and `article_revise` stages with `max_tokens` budget (1.8× target words for headroom) AND a `_user_prefix` ride-along that injects `"Target length: approximately N words"` into the user content.

### Verified
- Live A/B: same transcript at Brief vs Long-form produced 579 vs 3113 words (5.4× ratio, both within 16% of targets).
- Prompt-cache hit confirmed on every stage after the 0.6.1 default-user fix landed: `cache_read=5821` per call.
- 103 tests still pass.

## [0.6.1] - 2026-04-19

### Restored
- **Scanner line sweep** — the 1px-too-subtle scanner from pre-refactor was rebuilt at 2px with stronger glow + a proper 10s sweep that fades in/out at the edges.
- **Primary buttons** ("I'm Feeling Lucky", "Save to Notion") get a teal→purple→magenta gradient with a slow 6s sheen animation — replaces the old `.lucky-button` energy.
- **Ambient background drift** — 60s subtle gradient hue-shift on `.stApp` so the canvas feels alive.
- **Section-header underline** wipes in on first render (`scaleX 0→1` over 0.6s).
- **Pulse on active `sac.steps` step** — borrowed `@keyframes pulse` from the old `.process-indicator .dot`.
- **Bottom bar** gets a top-edge shimmer that breathes on an 8s cycle.
- **Bordered cards** have a hover-lift transition.

### Fixed
- **CSS selectors that didn't match Streamlit 1.56's actual DOM** (discovered by grepping `streamlit/static/*.js`):
  - `st.segmented_control` renders as `stButtonGroup`, NOT `stSegmentedControl`. The provider picker was unstyled before this fix.
  - `stVerticalBlockBorderWrapper` doesn't exist; bordered containers now match via `:has()` + `style*="border"` attribute selectors.
  - `st.status` shares the `stExpander` testid; both selectors applied as a pair.
- **Default user regression** — pass-1 of the refactor defaulted the sidebar to alphabetically-first user (`Caroline_Hilton` in Kris's tree), which has no KB. Result: every pipeline run since 0.6.0 ran with no KB injection → `cache_read=0` everywhere → ~67% prompt-cache savings silently disabled. Now `ui/session._resolve_default_user()` picks: persisted last-selection → first KB-having user → alphabetically first. The sidebar persists changes to `.cache/ui_preferences.json`.

## [0.6.0] - 2026-04-19

### Added
- **Three-zone app shell** (header / sidebar + main / fixed bottom bar), Cursor/Claude-Code style. `app.py` shrunk from 970 → 55 LoC; feature code moved to a new `ui/` package.
- **`ui/` package** split by concern:
  - `session.py` — single `init_all_state()` entrypoint; every session-state key lives in one place. New `clear_run()` preserves settings, zeros per-run state. Per-provider model memory via `remember_model_for_provider()`.
  - `shell.py` — header + `render_bottom_bar()` wrapped in `streamlit-extras.bottom_container` + `@st.fragment(run_every="2s")` for live cost/cache/calls/model readout without rerunning the pipeline.
  - `sidebar.py` — compact profile / provider (`st.segmented_control`) / model pickers + four dialog-opening action buttons.
  - `dialogs.py` — four `@st.dialog` modals for prompt editor (selectbox + one text_area, replacing 5 stacked editors), knowledge base manager, run history (`st.data_editor` + `LinkColumn` on Notion URLs), and clear-run confirm.
  - `input.py` — three tabs (Upload / Record / Paste) that all write to one `pending_input`, replacing ~400 LoC of near-duplicate handler code.
  - `pipeline.py` — `sac.steps` horizontal stage indicator plus `st.status` collapsible progress container with per-stage `write()` lines. Single entrypoint routes both Transcribe-only and Full-pipeline modes.
  - `output.py` — one bordered card per section via `st.container(border=True)`, `st.feedback("thumbs")` per section, single unified Save-to-Notion path (replaced three).
- Dependencies: `streamlit-extras>=0.4.0`, `streamlit-antd-components>=0.3.2`. Streamlit pin bumped to `>=1.37` for `@st.fragment`.
- New CSS components: `.bottom-bar`/`.bottom-metric`, `.sidebar-status`, `.status-dot.*` variants, segmented-control palette overrides, sac.steps palette overrides, dialog + popover styling — all matching the existing cyberpunk vibe.

### Changed
- Recording-tab auto-save-to-Notion (old behavior) replaced by the single explicit "Save to Notion" button in the unified Output card. All three input tabs now behave identically after submit.
- `st.spinner` + `st.empty` + manual markdown replaced by `st.status("…", expanded=True)` streaming per-stage log lines.
- `st.success` banners replaced by `st.toast` ephemeral notifications.

### Removed (9 dead CSS selectors + 2 broken scripts from styles.py)
- `.lucky-button`, `.quick-access`, `.quick-button`, `.content-section`, `.terminal-output`, `.process-indicator` (+ `@keyframes pulse`), `.notion-button`, `.scanner-line` (+ `@keyframes scanner-move` + its broken inline HTML), `.toast-notification` (+ `@keyframes toast-in`).
- `.status-container` / `.status-card` / `.status-value` — the old "System Status" three-card row whose JS tried to `innerHTML` static elements Streamlit just rerendered.
- `.app-footer` / `.footer-content` / `.footer-status` / `.footer-status-dot` / `.status-secure/.status-sovereignty/.status-offline .footer-status-dot` — replaced by the compact `.sidebar-status` line.

### Verified
- `pytest tests/ -q` → 103 pass (no regressions; UI isn't unit-tested by design).
- `tests/smoke.sh` → HTTP 200 on `/_stcore/health`.
- Every `.class` in `styles.py` has a matching emitter in `app.py` or `ui/*.py` (verified by a grep-both-ways script).
- Live boot: `streamlit run app.py` → three zones render, no exceptions in the server log, index HTML clean.

## [0.5.0] - 2026-04-19

### Added
- **Image generation via Google Nano Banana** (Gemini 2.5 Flash Image). Ported from `kk-ai-ecosystem/tools/image-gen/generate.py` — just the core generator, not the CLI or markdown-file parser. New `whisperforge_core/images.py` with `generate_image()`, `generate_images()` batch, `extract_prompts()` parser, and a YAML-backed style registry (`styles/image_styles.yaml` — kk, hopecode, bcai, upgrade). Pipeline gains `generate_images=True` flag that turns the `image_prompts` stage output into real PNGs saved to `.cache/images/<run>/`. Cost tracked per-image at ~$0.039 (flash) / ~$0.10 (pro preview).
- **Settings dashboard** in the sidebar: one "⚙️ Generation Settings" expander consolidates every pipeline knob (cleanup, chapters, agentic, fact-check, image generation + style + aspect ratio + model).
- **Image gallery** in the main area: after a run, generated images render as a 3-column grid with per-image download button; failures show a warning with the API error.
- Tightened the `image_prompts` DEFAULT_PROMPT to produce a numbered list with bold labels, which made the extractor reliable (5/5 prompts parsed in live test vs 1 before).

### Changed
- `extract_prompts()` now tries numbered-list → blockquote → numbered-heading → whole-text-fallback in priority order, tolerating multiple LLM output formats.
- `whisperforge_core/__init__.py` re-exports the `images` module.

## [0.4.0] - 2026-04-19

### Added
- **In-browser recording** via `st.audio_input` (native in Streamlit 1.35+). New "Record" tab alongside "Audio Upload" and "Text Input" with Transcribe + I'm Feeling Lucky buttons that wire straight through to the existing pipeline. No separate recording app needed.
- **Cost tracker** — new `whisperforge_core.cost` module with a session usage ledger, per-provider/model pricing table, and Anthropic cache-semantics-aware `estimate_cost()`. Every `llm._call` records token counts on success. Sidebar shows "Est. cost" + "Cache saved" metrics for the session.
- **Run history** — new `whisperforge_core.history` module writes a JSONL record to `.cache/history.jsonl` after each successful Notion save (title, link, provider/model, cost, cache savings, flags, audio filename). Sidebar "Recent runs" expander shows the last 8 with one-click Notion links.

### Changed
- `whisperforge_core/__init__.py` re-exports the new `cost` and `history` modules.

## [0.3.2] - 2026-04-19

### Added
- **Agentic article drafting** (opt-in via `agentic=True` or the "Agentic drafting" sidebar toggle). Single-shot `article_writing` becomes a three-pass flow: draft → critique → revise. New `DEFAULT_PROMPTS` entries for `article_critique` and `article_revise`. Verified live on a 3-topic clip: Haiku 4.5 produced 13 specific editorial notes addressing voice drift, invented framing, length discipline, and incomplete thoughts; revised article addressed each.
- **Fact-check pass** (opt-in via `fact_check=True` or the "Fact-check article" toggle). Reads the final article against the transcript, returns JSON list of claims not grounded in the source. Verified live: caught 4 real fabrications (invented launch dates, unsourced tool-behavior claims). New "Fact Check" toggle in Notion (green when clean, red with per-claim details when flagged).
- `PipelineResult` gains `article_draft`, `article_critique`, `fact_check_flags`. `ContentBundle` mirrors these so the editorial trail is auditable from Notion.

### Changed
- Fact-check (when combined with agentic) runs against the revised article, not the draft — so we're grounding the final product.

## [0.3.1] - 2026-04-19

### Added
- **Timestamp-aware chapters end-to-end.** WhisperX segments now thread UI → pipeline → chapter prompt → ContentBundle → Notion `[M:SS]` prefix. New `audio.TranscriptionDetails` dataclass and `audio.transcribe_audio_detailed()`; new `adapters.Transcriber.transcribe_detailed()` protocol method; new `chapters_timestamped` content_type that formats input as `[SSSS.S]` lines and asks the model to copy `start_seconds` per chapter. Verified live: 3-topic clip → chapters at 4.0s / 15.8s / 27.9s matching audio boundaries.

## [0.3.0] - 2026-04-19

### Added
- **Anthropic prompt caching** on KB + system blocks. KB goes first with `cache_control: {"type": "ephemeral"}`; per-stage prompt follows uncached. Verified: stages 2-5 of a pipeline run read ~5800 cached tokens at 0.1x input cost. ~67% input-token cost reduction per run.
- **Post-ASR cleanup stage** (opt-out via `cleanup=False`). New content_type `transcript_cleanup` runs as pipeline stage 0, strips fillers/false-starts/typos before downstream stages see the transcript. Steals Wispr Flow's signature move.
- **Chapterization stage** (opt-out via `chapters=False`). New content_type `chapters` produces `[{title, summary, start_quote}]` via JSON schema. `llm.generate_chapters()` helper parses defensively. Notion gets a new "Chapters" toggle above Transcription with bulleted entries and optional `[MM:SS]` prefix.
- **Structured Outputs** on title/summary/tags via OpenAI JSON schema mode. All regex fragility gone. Helpers upgraded from gpt-3.5-turbo to gpt-4o-mini.
- **WhisperX backend** (`TRANSCRIPTION_BACKEND=whisperx`). faster-whisper + wav2vec2 alignment + optional pyannote diarization. Model cache is per-process for fast repeat runs. Diarization labels each segment with `[SPEAKER_XX]` when `WHISPERX_DIARIZATION=1` and `WHISPERX_HF_TOKEN` is set.
- **Silero VAD chunker** (`CHUNKER=vad`). Cuts on silences instead of bytes, drops silent segments entirely, falls back to size-based on failure.
- New env knobs: `WHISPER_MODEL`, `CHUNKER`, `WHISPERX_MODEL`, `WHISPERX_DEVICE`, `WHISPERX_COMPUTE`, `WHISPERX_DIARIZATION`, `WHISPERX_HF_TOKEN`.

### Changed
- `LLM_MODELS` catalog refreshed again. Claude Haiku 4.5 added as new session-state default (fastest + in-voice). Sonnet 4.5 and Opus 4.5 kept as premium tiers.
- Cloud transcription default → `gpt-4o-mini-transcribe` (was `whisper-1`). Still pinnable via `WHISPER_MODEL`.
- `_call()` split for Anthropic to use structured `system` blocks (KB first with cache_control, prompt second uncached). OpenAI/Ollama paths unchanged, still flat string.
- `PipelineResult` gained `raw_transcript`, `cleaned_transcript`, `chapters` fields.
- `ContentBundle` gained `chapters` list field.

### Docs
- `readme.md` env-var reference table expanded with all new knobs.

## [0.2.1] - 2026-04-19

### Added
- Local model lanes: Ollama provider (OpenAI-compatible, `localhost:11434`) with auto-discovery of installed models via `llm.discover_ollama_models()`. MLX Whisper and whisper.cpp backends selectable via `TRANSCRIPTION_BACKEND=mlx|whisper_cpp`.
- Cache wiring — `WHISPERFORGE_CACHE=1` enables sha256-keyed result caching across `audio.transcribe_audio` and `llm.generate`. Never caches empty/None (so failures retry). 20 new unit tests covering the cache behavior.

### Changed
- `LLM_MODELS` catalog refreshed. Dropped Claude 3.x (retired from Anthropic's API). Added Claude Haiku 4.5 (new default), Sonnet 4.5, Opus 4.5. OpenAI adds gpt-4o and gpt-4o-mini; gpt-4 and gpt-4-turbo kept as legacy entries.
- Default provider/model in `main()` session-state init → Anthropic `claude-haiku-4-5` (fast, cheap, in-voice). Override in sidebar for premium or local.
- `transcribe_audio` small-file fast path now routes through `transcribe_chunk` so all three backends (openai / mlx / whisper_cpp) behave consistently.

### Fixed
- Key harvest from `kk-ai-ecosystem/.env` auto-populates `.env`; target Notion database (`WhisperForge DB`) auto-discovered via integration search.

### Removed (cleanup sweep)
- `monitoring/`, `scripts/`, `experiments/`, `services/auth/`, root `Dockerfile`, `setup.py`, `shared-requirements.txt`, `.DS_Store` (all dead).

### Docs
- Full `readme.md` rewrite: architecture diagram, "Running fully local" section, expanded env-var reference table.

## [0.2.0] - 2026-04-19

### Added
- `whisperforge_core/` package — shared business logic (audio, llm, notion, prompts, pipeline, cache, logging, adapters) used by both the monolith and the FastAPI microservices.
- `DEPLOY_MODE=direct|services` env flag selecting between local (in-process) and containerized (HTTP) backends via `whisperforge_core.adapters`.
- `styles.py` — all CSS extracted from `app.py`.
- Text-input tab can now save generated content to Notion (previously dead-ended).
- `requirements-services.txt` for the FastAPI stack; `audioop-lts` shim for Python 3.13 (pydub compat).

### Changed
- `app.py` shrunk 2302 → ~705 lines (thin UI shell over `whisperforge_core`).
- Services under `services/` rewritten as thin wrappers on `whisperforge_core`; `services/frontend/app.py` deleted in favor of a single canonical `app.py` that runs in both modes.
- `docker-compose.yml` rebuilt: adds missing `storage` service, removes orphaned `auth`/`postgres`/`admin`. Auth deferred for single-user deployments.
- `shared/security.py` simplified to an `X-API-Key: SERVICE_TOKEN` check (JWT deferred).
- Whisperforge CLI (`whisperforge.py`) is now a 45-line wrapper on `whisperforge_core.audio`.

### Fixed
- `requirements.txt` was the FastAPI/JWT stack instead of Streamlit — now lists the correct runtime deps.
- `shared/config.py` NameError on undefined `CLAUDE_API_KEY`.
- Deprecated `st.experimental_rerun()` → `st.rerun()`.
- Three bare `except:` clauses replaced with `except OSError:` for cleanup paths.

### Removed
- Grok provider support (endpoint unverified, only `grok-1` listed).
- Legacy `old_app.py` after salvaging logging + cache patterns.
- `services/admin/` (stubs, no Dockerfile), `services/shared/` (dup of `/shared/`), stale test files.

## [0.1.1] - 2024-03-20

### Added
- Automatic audio file chunking for files over 25MB
- Detailed progress logging in transcription service
- Extended timeout handling for large files

### Changed
- Reduced chunk size to 10MB for faster processing
- Transcription service timeout increased to 300s
- Frontend request timeout increased to 300s
- Improved error handling and logging
- Added bitrate compression for audio chunks

### Fixed
- Timeout issues with larger audio files
- Memory handling for large file processing
- Temporary file cleanup reliability

### Technical Details
- Chunk size: 10MB with 128k bitrate compression
- Max file size remains at 200MB
- Added progress tracking per chunk
- Enhanced error logging across services
- Improved temp file management

### Known Issues
- Limited progress feedback in frontend during chunking
- No automatic retry on chunk failure
- Processing time increases linearly with file size

## [0.1.0] - 2024-11-18

### Added
- Initial release
- Audio file upload and transcription
- Notion integration
- Insights extraction
- Language detection
- Chunking support for large files

### Fixed
- Notion emoji validation issue
- Audio processing compatibility with Python 3.11

## [Unreleased] - 2024-11-18
### Added
- Monitoring infrastructure with Prometheus and Grafana
- Basic Notion integration in storage service
- Health check endpoints across all services

### Changed
- Updated project structure with monitoring directory
- Enhanced error handling in storage service