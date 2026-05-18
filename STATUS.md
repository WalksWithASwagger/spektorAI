# WhisperForge Status

Last updated: 2026-05-17

## Current State

- Last verified checkout: `kk/swarm-roadmap-batch-1` at the current PR head
  after the documentation audit and PR-review follow-up fixes.
- Remote sync: `git fetch --prune origin` completed; all local tracking
  branches were even with their upstreams after fetch.
- Latest roadmap anchor: PR #10 head. Use `git log -1 --oneline` for the exact
  local commit because this status file is updated inside that PR stack.
- GitHub repo: `WalksWithASwagger/spektorAI`
- Linear project: [WhisperForge Roadmap](https://linear.app/bc-ai/project/whisperforge-roadmap-317805524537)
- Primary product surface: direct Streamlit mode (`streamlit run app.py`)
- Services mode: present. Processing/storage HTTP adapters now forward the
  modern payload contract; timestamped transcription segments are still a
  parity gap.

## Verified

- `git status --short --branch` -> clean checkout on
  `kk/swarm-roadmap-batch-1...origin/kk/swarm-roadmap-batch-1`
- `git rev-list --left-right --count HEAD...@{u}` -> `0 0`
- `git for-each-ref --format='%(refname:short) %(upstream:short) %(upstream:trackshort)' refs/heads`
  -> all local tracking branches showed `=`
- `make test` -> `169 passed`
- `make eval-fixture` -> credential-free editorial/source-receipt fixture OK
- `make smoke` -> Streamlit health OK on port `8599`
- `venv/bin/python tests/ui_smoke.py` -> rendered shell OK
- `python3 -m json.tool ops/roadmap/features.json` -> valid JSON
- `git diff --check` -> clean after the documentation audit follow-up fixes

## Active Handles

- Roadmap: `ROADMAP.md`
- Delivery workflow: `docs/LINEAR-GITHUB-PIPELINE.md`
- Backlog registry: `ops/roadmap/features.json`
- GitHub issues: `#1` through `#8`
- Linear issues: `BC-57`, `BC-58`, `BC-63`, `BC-73`, `BC-83`, `BC-88`, `BC-90`, `BC-91`
- `whisperforge-env/` has been removed from the git index and remains ignored.
- PR #10 contains the first roadmap swarm batch plus PR-review follow-up fixes.
  Verify GitHub/Linear live state before changing external issue or PR status.

## Known Risks

- `gh` was available and authenticated during the latest swarm resume, but
  connector-backed GitHub/Linear reads remain the safer fallback if auth drifts.
- `tests/smoke.sh` needs a free localhost port; the default is `8599`.
- Runtime MP3/M4A operations still need `ffmpeg` on `PATH`; the unit suite uses
  WAV fixtures so local tests can run without it.
- Services-mode transcription still returns text-only details, so timestamped
  chapter segments are not yet available over HTTP.
- Linear PR auto-linking should be verified on the first branch/PR that includes
  a `BC-*` issue key.
