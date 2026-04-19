# WhisperForge

Turn spoken thoughts into polished, publishable content. Upload audio, and
WhisperForge transcribes it, extracts wisdom, drafts an outline and article,
generates social posts + image prompts, and ships the bundle to a structured
Notion page — all tuned to your own voice via a per-user prompt and knowledge
base.

---

## Features

- **Audio transcription** (MP3, WAV, OGG, M4A) via OpenAI Whisper, with
  automatic chunking for files above 20 MB.
- **Three provider lanes**: OpenAI (cloud), Anthropic (cloud), or any local
  model running via Ollama (`localhost:11434`). Ollama models are
  auto-discovered at UI load.
- **Local-first transcription** available: MLX Whisper (Apple Silicon native)
  or whisper.cpp as alternates to the cloud Whisper API.
- **Five-stage pipeline** per run: wisdom → outline → social media → image
  prompts → full article draft.
- **Per-user voice**: prompts + knowledge base live under `prompts/<user>/`
  and are injected into the system prompt on every call.
- **Text-input mode**: paste prose instead of uploading audio and run the same
  pipeline (useful for imported transcripts).
- **Structured Notion export**: collapsible toggles per section, color-coded,
  AI-generated title + tags + summary, respecting Notion's block limits.
- **Two deployment modes**: single-process monolith for local use, or
  FastAPI microservices via `docker-compose` — same code, same UI.

---

## Architecture

```
whisperforge_core/            pure-logic package (no Streamlit)
├── config.py                 env, LLM catalog, defaults
├── logging.py                logger setup
├── cache.py                  file-hash pickle cache (sha256 + model + prompt)
├── prompts.py                user/KB discovery, override precedence
├── audio.py                  chunking + Whisper transcription
├── llm.py                    unified generate() for OpenAI/Anthropic
├── notion.py                 ContentBundle + 1900-char block chunker
├── pipeline.py               5-stage orchestration with progress callback
├── adapters.py               Local{Transcriber,Processor,Storage}
└── http_adapters.py          Http{Transcriber,Processor,Storage}

app.py                        Streamlit UI shell (imports whisperforge_core)
styles.py                     all CSS
whisperforge.py               45-line CLI wrapper for transcription only

services/
├── transcription/service.py  POST /transcribe → audio.transcribe_audio
├── processing/service.py     POST /generate, /pipeline → llm / pipeline
├── storage/service.py        POST /save → notion.create_page
└── frontend/Dockerfile       builds root app.py with DEPLOY_MODE=services

shared/                       cross-service config + X-API-Key auth
tests/                        pytest suite (38 tests) + smoke.sh
prompts/<user>/               prompts, knowledge_base, custom_prompts
```

The monolith (`streamlit run app.py`) imports `whisperforge_core` directly. In
services mode (`docker compose up`), the same `app.py` runs inside a `frontend`
container and talks to the three FastAPI services over HTTP via
`http_adapters`. Swap by setting `DEPLOY_MODE=direct` (default) or `services`.

---

## Setup

### Prerequisites

- Python 3.10+ (tested on 3.11 and 3.13; `audioop-lts` shim pinned for 3.13)
- `ffmpeg` on `PATH` (`brew install ffmpeg` on macOS)
- OpenAI and Notion API keys; Anthropic key optional but recommended

### Install

```bash
git clone <your-fork-url> spektorAI
cd spektorAI
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configure `.env`

```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...
NOTION_API_KEY=secret_...
NOTION_DATABASE_ID=<your-database-id>

# Only needed for services mode (docker compose):
SERVICE_TOKEN=<any-shared-secret>
```

### Create your prompt profile (first run only)

```bash
mkdir -p prompts/<YourName>/{prompts,knowledge_base,custom_prompts}
```

Drop `.md` prompt templates into `prompts/<YourName>/prompts/` and voice/style
docs into `prompts/<YourName>/knowledge_base/`.

---

## Running

### Monolith (local, recommended for daily use)

```bash
streamlit run app.py
# → http://localhost:8501
```

### Microservices (docker-compose)

```bash
docker compose up --build
# → http://localhost:8501
```

Four containers come up: `transcription`, `processing`, `storage`, `frontend`.
The frontend's `DEPLOY_MODE=services` env var tells it to HTTP-call the
backends.

### CLI (transcription only)

```bash
python whisperforge.py path/to/audio.m4a [transcript.txt]
```

### Running fully local (no cloud inference)

You can run the whole transcription + content pipeline on-device, with only
Notion requiring network access:

```bash
# 1. Pull an LLM via Ollama (llama3 works; larger models write better)
ollama pull llama3

# 2. Enable the local backends
export TRANSCRIPTION_BACKEND=mlx           # Apple Silicon
export MLX_WHISPER_MODEL=mlx-community/whisper-medium-mlx  # medium recommended

# 3. Run normally
streamlit run app.py
# then in the sidebar: AI Provider → "Ollama (local)" → pick a model
```

The installed Ollama models are auto-discovered at sidebar load, so new
`ollama pull`s appear without restarting. Transcription backends available:
`openai` (cloud default), `mlx` (local Apple Silicon via `mlx-whisper`), and
`whisper_cpp` (local via the `whisper-cli` binary; set `WHISPER_CPP_MODEL` to
a ggml bin path).

---

## Workflow

1. **Pick your user profile** in the sidebar. Any directory under `prompts/`
   becomes a profile.
2. **Select provider + model** (OpenAI or Anthropic).
3. **Upload audio or paste text.** Large audio is chunked automatically.
4. **Generate** — run individual stages (Extract Wisdom, Create Outline,
   Social, Image Prompts, Full Article) or use "I'm Feeling Lucky" to run the
   whole pipeline sequentially with a progress bar.
5. **Save to Notion** — builds a single page with color-coded toggles per
   section, an AI-generated title, summary callout, tags, and metadata
   footer (audio filename, timestamp, models used, token estimate).

### Notion page layout

```
WHISPER: <AI-generated title>
  💜 callout with one-sentence summary
  ─── divider ───
  ▶ Transcription           (default toggle)
  ▶ Wisdom                  (brown)
  ▶ Socials                 (orange)
  ▶ Image Prompts           (green)
  ▶ Outline                 (blue)
  ▶ Draft Post              (purple)
  ▶ Original Audio          (red; only if audio was uploaded)
  ─── Metadata ───
  Original Audio · Created · Models Used · Estimated Tokens
Properties: Name, Tags (multi-select, AI-generated)
```

---

## Customising prompts and knowledge base

Three override layers per user, resolved in precedence order:

1. `prompts/<user>/custom_prompts/<type>.txt` — highest priority, saved by the
   in-app "Save Prompt" button.
2. `prompts/<user>/prompts/<type>.md` — on-disk template.
3. `whisperforge_core.config.DEFAULT_PROMPTS[<type>]` — fallback.

Valid `<type>` values: `wisdom_extraction`, `summary`, `outline_creation`,
`social_media`, `image_prompts`, `article_writing`, `seo_analysis`.

**Knowledge base** files at `prompts/<user>/knowledge_base/*.{md,txt}` are
prepended to the system prompt on every LLM call, so the model writes in your
voice and with your context.

---

## Development

### Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -q          # 38 unit tests, ~1s
tests/smoke.sh            # boots streamlit, hits /_stcore/health
```

### Directory structure for day-to-day work

- **Fixing bugs in the pipeline?** Edit `whisperforge_core/` — all business
  logic lives there. The monolith and services both pick up the change.
- **Tweaking UI or CSS?** `app.py` for layout, `styles.py` for CSS.
- **Changing Notion layout?** `whisperforge_core/notion.py`. Preserve the
  1900-char block chunker — `tests/test_notion.py` pins that invariant.
- **Adding a provider?** Add a branch in `whisperforge_core/llm._call` and
  extend `LLM_MODELS` in `config.py`.

### Configuration reference

| Env var             | Purpose                                         | Required      |
| ------------------- | ----------------------------------------------- | ------------- |
| `OPENAI_API_KEY`    | Whisper + GPT models                            | yes           |
| `ANTHROPIC_API_KEY` | Claude models                                   | recommended   |
| `NOTION_API_KEY`    | Notion integration                              | yes           |
| `NOTION_DATABASE_ID`| Destination database ID                         | yes           |
| `DEPLOY_MODE`       | `direct` (default) or `services`                | no            |
| `SERVICE_TOKEN`     | Shared X-API-Key for inter-service calls        | services mode |
| `WHISPERFORGE_LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` (default INFO) | no          |
| `WHISPERFORGE_CACHE_DIR` | Cache location (default `.cache/`)          | no            |
| `WHISPERFORGE_CACHE`     | `1` to enable the transcription/LLM cache    | no            |
| `TRANSCRIPTION_BACKEND`  | `openai` (default) \| `mlx` \| `whisper_cpp` \| `whisperx` | no |
| `WHISPERX_MODEL`         | faster-whisper model size (`tiny`\|`base`\|`small`\|`medium`\|`large-v3`; default `small`) | no |
| `WHISPERX_DEVICE`        | `cpu` (default) or `cuda`                    | no            |
| `WHISPERX_DIARIZATION`   | `1` to label speakers via pyannote           | no            |
| `WHISPERX_HF_TOKEN`      | HuggingFace token (required when diarization is on) | diar only |
| `WHISPER_MODEL`          | Cloud Whisper model (default `gpt-4o-mini-transcribe`; also `gpt-4o-transcribe` or `whisper-1`) | no |
| `MLX_WHISPER_MODEL`      | HF repo for mlx-whisper (default whisper-medium-mlx) | no    |
| `WHISPER_CPP_MODEL`      | Path to ggml bin for `whisper_cpp` backend   | whisper_cpp only |
| `CHUNKER`                | `size` (default) \| `vad` (Silero VAD, cuts on silence) | no        |
| `OLLAMA_BASE_URL`        | Override Ollama endpoint (default `http://localhost:11434/v1`) | no |
| `TRANSCRIPTION_URL` / `PROCESSING_URL` / `STORAGE_URL` | Override service URLs (docker-compose sets these) | no |

---

## Changelog

See [`changelog.md`](changelog.md). The 2026-04-19 refactor (0.2.0) collapsed
the previous two parallel implementations into a single shared-logic package,
dropped Grok, fixed `requirements.txt`, and added the test suite.

## License

Unlicensed / private. Not for distribution.
