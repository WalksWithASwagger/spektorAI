# AGENTS.md

How to work in this repo, for humans and their agents.

## what this is
spektorAI is the home of WhisperForge, a local-first Streamlit voice-to-knowledge workbench: audio or dictation in, source-grounded draft + social + Notion page out.

## ground rules
- match the existing style. surgical changes only.
- public copy follows the house voice: see kk-brand/VOICE.md. full punk, no em dashes.
- business logic lives in `whisperforge_core/`. UI and CSS live in `ui/` and `styles.py`. `app.py` is just the composition root.
- the Makefile is the command surface. `make app` runs it, `make test` runs the suite, `make smoke` boots the shell and hits health, `make docs-check` checks doc truth.
- read `.env.schema` for the authoritative Varlock env contract. reusable values may come from the selective, optional imports under `~/.agents/env/values/`; never create or inspect that directory, any `.env*` value file, the process environment, Keychain, or another credential store.
- use `make env-check` for Varlock's agent-safe env summary. if Varlock is not on `PATH`, run `VARLOCK=/path/to/varlock make env-check`.
- run real provider/service commands through `varlock run --inject vars -- <command>`. keep offline `make app` behavior dummy-env friendly.
- keep application runtimes unchanged. Varlock 1.10 validation uses Node 22.3+ or the standalone CLI.
- routing stays dry-run by default. handoffs to GitHub/Linear/Notion, paid-provider swaps, deploys, and external sends need explicit human approval. do not flip those on your own.
- no open-source license is granted. treat the code as source-available for collaboration, not freely redistributable.

## the maker
Kris Krüg (@WalksWithASwagger) · https://kriskrug.co · BC + AI
