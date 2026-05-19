# WhisperForge

Canonical repository: `WalksWithASwagger/spektorAI`.

Turn spoken thoughts into polished, publishable content. Upload audio, and
WhisperForge transcribes it, extracts wisdom, drafts an outline and article,
generates social posts + image prompts, and ships the bundle to a structured
Notion page — all tuned to your own voice via a per-user prompt and knowledge
base.

Legacy audio repositories are being archived as historical pointers after the
May 2026 consolidation audit. Treat this repo as the source of truth for
WhisperForge implementation, roadmap, and issue work.

---

## Features

**Audio in**
- MP3 / WAV / OGG / M4A upload OR record live in the browser via
  `st.audio_input` — no external recorder needed.
- Four transcription backends: OpenAI cloud Whisper (`gpt-4o-mini-transcribe`
  default), **MLX Whisper** (Apple Silicon native), **whisper.cpp** (CPU/Metal),
  **WhisperX** with word-level timestamps + optional pyannote speaker
  diarization. See
  [`docs/TRANSCRIPTION-PROVIDER-MATRIX-2026-05-18.md`](docs/TRANSCRIPTION-PROVIDER-MATRIX-2026-05-18.md)
  before adding another provider or changing defaults.
- Silero VAD-based chunker (opt-in) cuts on silences instead of byte size.

**Pipeline**
- Three LLM provider lanes: **OpenAI**, **Anthropic**, or local **Ollama**
  (auto-discovers installed models at UI load).
- Default: **Claude Haiku 4.5** — fast, cheap, in your voice.
- Stages: transcript cleanup → chapters → wisdom → outline → social → image
  prompts → article → optional critique/revise → optional fact-check →
  optional image generation.
- **Agentic drafting**: draft → critique → revise for publishable long-form.
- **Fact-check pass**: flags article claims not grounded in the transcript.
- **Chapterization**: topical segmentation with `[M:SS]` timestamps when
  WhisperX is the backend; JSON-schema-enforced output.
- **Anthropic prompt caching** on the knowledge-base prefix — ~67% input-
  token cost reduction per 5-stage run.
- **Per-user voice**: prompts + knowledge base live under `prompts/<user>/`
  and are injected into the system prompt on every call.
- **Text-input mode**: paste prose instead of uploading audio and run the same
  pipeline (useful for imported transcripts).
- **Capture inbox**: Wispr Flow dictation, pasted notes, uploads, and browser
  recordings become durable capture records under `.cache/captures/`, then link
  to run artifacts and exports.
- **KB health + retrieval inspection**: the Knowledge Base dialog inventories
  files, flags stale/duplicate/private-looking signals, and can show the exact
  RAG chunks, scores, and voice anchors selected for a sample query.
- **Recipe command palette**: choose reusable workflows such as article with
  receipts, brief/social pack, or issue handoff; recipes apply saved defaults
  while preserving the manual controls.
- **Composition review**: the Output card includes a Review tab where the draft
  sits beside source receipts, excerpts, claim flags, revision notes, compare
  variants, and persona variants before export.
- **Advisory scorecards**: deterministic, credential-free checks summarize
  voice, grounding, usefulness, recipe compliance, and handoff readiness without
  blocking saves.
- **Agent handoff drafts**: the Review tab can turn a capture, transcript, or
  selected output into a GitHub/Linear-ready issue brief and persist the dry-run
  draft under the current run artifacts.
- **Run workspace**: the Runs dialog reads `.cache/runs` manifests, flags
  partial/error runs, and can reopen completed outputs so Markdown, Notion, or
  handoff exports can be retried without regenerating content.
- **Resurfacing digest**: `make digest` generates a local report-only digest of
  notable captures, unresolved follow-ups, strong outputs, stale drafts, and
  reusable source nuggets.
- **SongForge creative lane**: the SongForge recipe turns a capture plus
  selected KB context into original lyrics, a spoken-word variant, a
  service-agnostic music prompt pack, and source notes.

**Image generation**
- Google Nano Banana (Gemini 2.5 Flash Image) turns the `image_prompts` stage
  output into real PNGs — ~$0.039/image flash, ~$0.10/image pro.
- Four style presets (`kk`, `hopecode`, `bcai`, `upgrade`) with brand-specific
  prompt suffixes; see `styles/image_styles.yaml`.
- Aspect-ratio presets (16:9, 1:1, 9:16) for LinkedIn, Instagram, Stories.

**Output**
- Structured **Notion export**: collapsible toggles per section, color-coded,
  AI-generated title + tags + summary, Chapters with `[M:SS]` jump prefixes,
  Revision Notes + Fact Check toggles when agentic/fact-check ran.
- **Markdown + Notion scorecards**: advisory verdicts travel with saved/exported
  runs and show up in Recent Runs.
- **Cost tracker** (session total + cache savings) and **Run history**
  (clickable list of recent Notion pages) in the sidebar.

**Deployment**
- Single-process **monolith** for local use.
- **Microservices** via `docker-compose` — same UI, FastAPI workers wrap the
  same shared-logic package.

---

## Interface

Three zones: header, sidebar + main stream, fixed bottom status bar.

```
┌──────────────────────────────────────────────────────────────────┐
│  WhisperForge // Control_Center              Wed 19 Apr · 17:00  │
├──────────┬───────────────────────────────────────────────────────┤
│ PROFILE  │  ┌─ Input ─────────────────────────────────────────┐ │
│  KK ▾    │  │ [📂 Upload] [🎙 Record] [✎ Paste]                │ │
│          │  └─────────────────────────────────────────────────┘ │
│ PROVIDER │  ┌─ Pipeline ──────────────────────────────────────┐ │
│  Haiku ▾ │  │ ● Transcribe ● Clean ● Wisdom ○ Article ○ ...   │ │
│          │  │ Streaming status logs (st.status)                │ │
│ ⚙ More   │  └─────────────────────────────────────────────────┘ │
│ 📜 Runs  │  ┌─ Output ────────────────────────────────────────┐ │
│ ✎ Prompts│  │ 📝 Article · 🎯 Wisdom · 🗺 Outline · 🖼 Images │ │
│ 📚 KB    │  │ 👍👎 feedback per section · 📤 Save to Notion   │ │
│          │  └─────────────────────────────────────────────────┘ │
├──────────┴───────────────────────────────────────────────────────┤
│ Cost $0.12 · Calls 4 · Cache saved $0.03 · Claude Haiku 4.5      │
└──────────────────────────────────────────────────────────────────┘
```

All heavy trees (Prompt editor, Knowledge Base manager, Run history) live
in `@st.dialog` modals triggered from the sidebar — the sidebar itself
stays compact. Generation Settings (cleanup, chapters, agentic, fact-check,
images + style/ratio/model) live in the `⚙ More` popover.

The bottom bar polls cost + cache savings every 2 s via `@st.fragment`
without rerunning the pipeline.

## Architecture

```
whisperforge_core/            pure-logic package (no Streamlit)
├── config.py                 env, LLM catalog, defaults
├── logging.py                logger setup
├── cache.py                  file-hash pickle cache (sha256 + model + prompt)
├── prompts.py                user/KB discovery, override precedence
├── audio.py                  chunking + Whisper transcription
├── llm.py                    unified generate() for OpenAI/Anthropic/Ollama
├── notion.py                 ContentBundle + 1900-char block chunker
├── pipeline.py               orchestration with progress callback
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
tests/                        229 tests + health/rendered UI smokes
prompts/<user>/               profile.yaml, prompt .md files, knowledge_base,
                               personas, custom_prompts
```

The monolith (`streamlit run app.py`) imports `whisperforge_core` directly. In
services mode (`docker compose up`), the same `app.py` runs inside a `frontend`
container and talks to the three FastAPI services over HTTP via
`http_adapters`. Swap by setting `DEPLOY_MODE=direct` (default) or `services`.
Direct mode is the primary product surface. Services mode shares the modern
processing/storage payload contract; timestamped transcription segments are
still a direct-mode feature until the transcription service serializes them.

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

# Only needed for image generation (Nano Banana / Gemini):
GOOGLE_API_KEY=AIzaSy...

# Only needed for services mode (docker compose):
SERVICE_TOKEN=<any-shared-secret>
```

If you haven't created a Notion database yet, invite your integration to any
Notion database with `Name` and `Tags` properties — WhisperForge will
auto-discover it via the integration's `search` API.

### Create your prompt profile (first run only)

```bash
mkdir -p prompts/<YourName>/{knowledge_base,personas,custom_prompts}
```

Drop prompt templates directly into `prompts/<YourName>/<type>.md`, optional
persona directives into `prompts/<YourName>/personas/*.md`, and voice/style
docs into `prompts/<YourName>/knowledge_base/`. Use
`prompts/<YourName>/profile.yaml` when a profile needs manifest-defined prompt
or persona overrides.

---

## Running

### Monolith (local, recommended for daily use)

```bash
make app
# → http://localhost:8501
```

Override the port with `PORT=8502 make app`. The target defaults missing API
keys to dummy values so agents can verify the Streamlit shell without touching
real services.

### Microservices (docker-compose)

```bash
make services-run
# → http://localhost:8501
```

Four containers come up: `transcription`, `processing`, `storage`, `frontend`.
The frontend's `DEPLOY_MODE=services` env var tells it to HTTP-call the
backends.

Use `make services-smoke` for an operations smoke: it builds and starts the
compose stack, waits for container health checks, curls the frontend
`/_stcore/health` endpoint, and then stops the stack. Services mode requires
Docker and a local `.env` with `SERVICE_TOKEN`.

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
a ggml bin path), and `whisperx` (word timestamps plus optional pyannote
diarization). Provider tradeoffs and candidate integrations are tracked in
[`docs/TRANSCRIPTION-PROVIDER-MATRIX-2026-05-18.md`](docs/TRANSCRIPTION-PROVIDER-MATRIX-2026-05-18.md).

---

## Workflow

1. **Pick your user profile** in the sidebar. Any directory under `prompts/`
   becomes a profile.
2. **Select provider + model** (OpenAI, Anthropic, or Ollama).
3. **Upload audio, paste text, or paste Wispr Flow dictation.** Each submitted
   input is normalized into a capture record.
4. **Generate** — run individual stages (Extract Wisdom, Create Outline,
   Social, Image Prompts, Full Article), use "I'm Feeling Lucky" for manual
   settings, or pick a recipe from the command palette and run it from the
   current capture/input.
5. **Save to Notion** — builds a single page with color-coded toggles per
   section, an AI-generated title, summary callout, tags, run metrics, and
   metadata footer. A local markdown export can be written alongside the
   Notion save, and each run writes inspectable artifacts under `.cache/runs/`.

Use the Output card's **Review** tab when a draft needs source-grounded
judgment before publishing. It summarizes available receipts, transcript/KB
excerpts, fact-check flags, revision notes, compare output, and persona
variants, plus an advisory scorecard for voice, grounding, usefulness, recipe
compliance, and handoff readiness. It is a review surface, not a collaborative
editor; edits still happen by rerunning with adjusted prompts, recipes, or
settings. The same tab includes an **Agent handoff draft** preview that writes
local issue drafts only; external tracker creation remains a separate explicit
action. Use the sidebar's **Runs** dialog to reopen completed run artifacts
into this output/review surface and retry downstream exports. Partial runs are
listed with their last stage and errors, but arbitrary stage replay is still out
of scope.

### Notion page layout

```
WHISPER: <AI-generated title>
  💜 callout with one-sentence summary
  ─── divider ───
  ▶ Chapters                (when enabled)
  ▶ Transcription           (default toggle)
  ▶ Wisdom                  (brown)
  ▶ Socials                 (orange)
  ▶ Image Prompts           (green)
  ▶ Outline                 (blue)
  ▶ Draft Post              (purple)
  ▶ Article · <compare>     (when A/B compare ran)
  ▶ Persona · <name>        (one per selected persona)
  ▶ Scorecard               (advisory verdict + dimension scores)
  ▶ Original Audio          (red; only if audio was uploaded)
  ▶ Source Receipts         (transcript/evidence/composition review receipts)
  ▶ Run metrics             (cost, cache, settings, duration)
  ─── Metadata ───
  Original Audio · Created · Models Used · Estimated Tokens
Properties: Name, Tags (multi-select, AI-generated)
```

### Run recovery

The sidebar **Runs** dialog reads local manifests from `.cache/runs/`, not only
successful Notion history. It shows status, created/updated timestamps, input
type, recipe/settings, exports, partial-state flags, and errors. Completed runs
with a saved `session_output` stage can be reopened into the Output/Review
surface; from there, retry safe downstream work such as Markdown export, Notion
save, or agent handoff draft generation. Partial runs are visible for diagnosis,
but arbitrary stage replay and destructive cleanup are intentionally out of
scope.

---

## Customising prompts and knowledge base

Four override layers per user, resolved in precedence order:

1. `prompts/<user>/profile.yaml` prompt/persona entries — highest priority.
2. `prompts/<user>/custom_prompts/<type>.txt` — saved by the in-app
   "Save Prompt" button.
3. `prompts/<user>/<type>.md` — on-disk template.
4. `whisperforge_core.config.DEFAULT_PROMPTS[<type>]` — fallback.

Valid `<type>` values: `transcript_cleanup`, `chapters`,
`chapters_timestamped`, `wisdom_extraction`, `summary`, `outline_creation`,
`social_media`, `image_prompts`, `article_writing`, `article_critique`,
`article_revise`, `article_fact_check`, and `seo_analysis`.

**Knowledge base** files at `prompts/<user>/knowledge_base/*.{md,txt}` are
prepended to the system prompt on every LLM call, so the model writes in your
voice and with your context.

Use the sidebar's **KB** dialog to inventory the profile's KB files and catch
empty, duplicate, stale, oversized, or private-looking docs before they confuse
the pipeline. Use **Benchmark** to compare whole-KB injection vs RAG and inspect
the concrete retrieved chunks for a stage/query.

**Persona** files at `prompts/<user>/personas/*.md` appear beside the built-in
persona variants in Generation Settings.

**Recipes** are small YAML or JSON manifests that describe reusable command
palette workflows. Defaults live in
`whisperforge_core/recipe_defaults.yaml`; profile-specific recipes can be added
under `prompts/<user>/recipes/*.yaml` or the `recipes:` section of
`prompts/<user>/profile.yaml`. A recipe can declare `inputs`, `stages`,
`defaults` (`provider`, `model`, `kb_mode`, `article_length`, `cleanup`,
`chapters`, `agentic`, `fact_check`, `images`, `auto_export_markdown`),
`output_sections`, `eval_checks`, and `handoff_targets`.

`profile.yaml` can also act as a small profile operating-system manifest. These
fields are additive; profiles without them still load normally. Use the KB
dialog's **Profile OS summary** to inspect effective project context, defaults,
KB packs, privacy notes, handoff targets, and validation warnings.

```yaml
display_name: KK
project:
  name: WhisperForge
  context: Source-grounded content and agent handoffs
defaults:
  provider: Anthropic
  model: claude-haiku-4-5
  kb_mode: auto
kb_packs:
  voice:
    files:
      - knowledge_base/voice.md
privacy:
  notes: Internal drafts until explicitly exported
handoff_targets:
  - github
  - linear
  - markdown
```

---

## Development

### Tests

```bash
pip install -r requirements-dev.txt
make test                 # unit tests
make eval-fixture         # credential-free editorial/source-receipt fixture
make digest               # report-only resurfacing digest from local artifacts
make smoke                # boots streamlit, hits /_stcore/health
SMOKE_PORT=8601 make smoke
venv/bin/python tests/ui_smoke.py  # renders the Streamlit shell without a browser driver
```

Run `make help` for the full operations command list. The Makefile is the
preferred command surface for agents and CI snippets; the underlying commands
remain plain `pytest`, `streamlit`, and `docker compose`.

Run `make digest` weekly, or after a heavy capture/editing session, to surface
useful signal without routing it anywhere. The digest is local and report-only:
it links back to captures, run manifests, and exports, but it does not email,
post, create issues, or schedule follow-ups unless a later explicit workflow
adds that routing.

### Directory structure for day-to-day work

- **Fixing bugs in the pipeline?** Edit `whisperforge_core/` — all business
  logic lives there. The monolith and services both pick up the change.
- **Tweaking UI or CSS?** Edit `ui/` for Streamlit controls/layout and
  `styles.py` for CSS; `app.py` is only the composition root.
- **Changing Notion layout?** `whisperforge_core/notion.py`. Preserve the
  1900-char block chunker — `tests/test_notion.py` pins that invariant.
- **Adding a provider?** Add a branch in `whisperforge_core/llm._call` and
  extend `LLM_MODELS` in `config.py`.
- **Changing services mode?** Update both the FastAPI service model and
  `whisperforge_core/http_adapters.py`, then add a contract test.

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
| `WF_RAG`                 | Force RAG on/off (`1`/`true` or `0`/`false`) | no            |
| `WF_RAG_TOPK`            | Retrieved KB chunks per stage (default `5`) | no            |
| `WF_RAG_THRESHOLD`       | Auto-RAG chunk threshold (default `25`)     | no            |
| `WF_EMBED_MODEL`         | Sentence-transformer model for RAG          | no            |
| `TRANSCRIPTION_BACKEND`  | `openai` (default) \| `mlx` \| `whisper_cpp` \| `whisperx` | no |
| `WHISPERX_MODEL`         | faster-whisper model size (`tiny`\|`base`\|`small`\|`medium`\|`large-v3`; default `small`) | no |
| `WHISPERX_DEVICE`        | `cpu` (default) or `cuda`                    | no            |
| `WHISPERX_DIARIZATION`   | `1` to label speakers via pyannote           | no            |
| `WHISPERX_HF_TOKEN`      | HuggingFace token (required when diarization is on) | diar only |
| `GOOGLE_API_KEY`         | Gemini API key for image generation          | images only   |
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

## Roadmap

See [`ROADMAP.md`](ROADMAP.md) for the current stabilization and product
direction. The Linear/GitHub delivery workflow lives in
[`docs/LINEAR-GITHUB-PIPELINE.md`](docs/LINEAR-GITHUB-PIPELINE.md), with the
machine-readable backlog in [`ops/roadmap/features.json`](ops/roadmap/features.json).
Current handoff state lives in [`STATUS.md`](STATUS.md).

## License

Unlicensed / private. Not for distribution.
