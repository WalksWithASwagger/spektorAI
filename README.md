```text
K R Ü G  ··  spektorAI
the future belongs to the weird
```

# spektorAI

`talk your thoughts. get back a draft in your voice, with receipts.`

spektorAI is the home of WhisperForge, the voice-to-knowledge workbench I use to turn spoken thoughts into publishable work without losing my own voice. I dictate or upload audio, it transcribes, pulls the wisdom, drafts an article, writes the social posts and image prompts, and ships the whole bundle to a structured Notion page. it runs local-first as a Streamlit app on my machine. the voice comes from a per-user prompt and knowledge base, so the output sounds like me and not like a content mill.

it is built for people who think out loud and hate doing the same cleanup-and-formatting grind twice. it is not a hosted SaaS. you run it from a checkout, your keys stay where you put them, and nothing leaves the machine unless you send it somewhere on purpose.

## what it does

- take a Wispr Flow dictation, a pasted note, an upload, or a live browser recording, and turn it into one durable capture
- transcribe locally on Apple Silicon, on CPU, or in the cloud · your call, your tradeoff
- run the pipeline: clean the transcript, pull chapters and wisdom, draft an outline, write the article, spin up social posts and image prompts
- draft, critique, revise. a fact-check pass flags claims the transcript does not actually back up
- write in your voice via prompts + a knowledge base under `prompts/<user>/`, injected on every call
- review a draft next to its source receipts before anything ships. advisory scorecards, no gatekeeping
- hand off a capture or output as a GitHub or Linear issue draft. routing stays dry-run until you approve it
- ship a clean, color-coded Notion page with title, tags, summary, and run metrics
- pick your writing engine: OpenAI, Anthropic, or local Ollama. default is Claude Haiku 4.5, fast and cheap and in your voice

## start here

needs Python 3.10+ and `ffmpeg` on your PATH (`brew install ffmpeg` on macOS).

```bash
git clone https://github.com/WalksWithASwagger/spektorAI.git
cd spektorAI
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add OPENAI_API_KEY + NOTION keys, ANTHROPIC_API_KEY recommended
make app               # → http://localhost:8501
```

## environment contract

`.env.example` is the human setup template. `.env.schema` is the authoritative Varlock contract agents can read for env names, defaults, and sensitivity. It selectively imports reusable values from `~/.agents/env/values/.env.shared.local` and optional SpektorAI overrides from `~/.agents/env/values/.env.spektorai.local`; both imports allow missing files so CI and other machines stay portable. The user owns those local files. Agents must not create or inspect that directory, any `.env*` value file, the process environment, Keychain, or another credential store.

Use `make env-check` to run Varlock's agent-safe schema check. The command uses agent mode so runtime values stay redacted. If Varlock is not on `PATH`, point the Makefile at the CLI:

```bash
VARLOCK=/path/to/varlock make env-check
```

Keep the application runtime unchanged. Varlock 1.10 validation requires Node 22.3+ or the standalone CLI.

Run a credential-free fixture check through the same runtime injection boundary:

```bash
varlock run --inject vars -- make eval-fixture
```

`make app` still supplies dummy env values when real keys are absent, so offline local UI checks keep working without provider calls.

The schema covers the providers and transcription backends implemented in this repository. Candidate providers stay outside the runtime contract until their integrations exist.

GitHub-owned `GH_TOKEN`, `GITHUB_*`, and `RUNNER_*` names plus container-only `PYTHONPATH` and `PYTHONUNBUFFERED` settings are intentionally external to the application schema. Make-only `PYTHON`, `PORT`, `SMOKE_PORT`, `COMPOSE`, and `VARLOCK` overrides are command-surface controls and stay external too.

full setup, the provider matrix, and the run-recovery flow live in the engine handbook, [`WHISPERFORGE.md`](WHISPERFORGE.md). roadmap: `ROADMAP.md`. current handoff state: `STATUS.md`.

## these repos run on agents

built to be operated by humans and machines. see `AGENTS.md` and `llms.txt`.

---
> i don't build systems that optimize humans. i craft spaces where humans can be gloriously inefficient, creative, and alive.

made by Kris Krüg · [@WalksWithASwagger](https://github.com/WalksWithASwagger) · [kriskrug.co](https://kriskrug.co)
