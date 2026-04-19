# WhisperForge Changelog

All notable changes to WhisperForge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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