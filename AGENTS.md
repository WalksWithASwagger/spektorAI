# AGENTS.md

How to work in this repo, for humans and their agents.

## what this is
spektorAI is the home of WhisperForge, a local-first Streamlit voice-to-knowledge workbench: audio or dictation in, source-grounded draft + social + Notion page out.

## ground rules
- match the existing style. surgical changes only.
- public copy follows the house voice: see kk-brand/VOICE.md. full punk, no em dashes.
- business logic lives in `whisperforge_core/`. UI and CSS live in `ui/` and `styles.py`. `app.py` is just the composition root.
- the Makefile is the command surface. `make app` runs it, `make test` runs the suite, `make smoke` boots the shell and hits health, `make docs-check` checks doc truth.
- routing stays dry-run by default. handoffs to GitHub/Linear/Notion, paid-provider swaps, deploys, and external sends need explicit human approval. do not flip those on your own.
- no open-source license is granted. treat the code as source-available for collaboration, not freely redistributable.

## the maker
Kris Krüg (@WalksWithASwagger) · https://kriskrug.co · BC + AI

## Secrets (Varlock)

Inspect: `varlock load --agent`. Run tools: `varlock run --inject vars -- <command>`. Shared keys use Keychain accounts `kk-shared:local:<NAME>`. Do not read `.env*` value files in agent sessions.
