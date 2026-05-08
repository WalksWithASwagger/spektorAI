# Linear/GitHub Delivery Pipeline

Last updated: 2026-05-08

This repo follows the same delivery shape that worked for the kk-kb/cmvan
workflow: a roadmap registry in git, implementation issues in GitHub, and
project tracking in Linear.

## Surfaces

- Repository: `WalksWithASwagger/spektorAI`
- Local checkout: `/Users/kk/Code/spektorAI`
- Roadmap: [`../ROADMAP.md`](../ROADMAP.md)
- Backlog registry: [`../ops/roadmap/features.json`](../ops/roadmap/features.json)
- Linear team: `Bc-ai` (`BC`)
- Linear project: [WhisperForge Roadmap](https://linear.app/bc-ai/project/whisperforge-roadmap-317805524537)

## Workflow

1. Keep `ROADMAP.md` as the narrative source of direction.
2. Keep `ops/roadmap/features.json` as the machine-readable issue registry.
3. Create one GitHub issue per implementation-sized unit.
4. Create one Linear issue for the same unit and attach the GitHub issue URL.
5. Record both handles in `features.json`.
6. When implementing, create branches from the Linear suggested branch name when
   possible, or at least include the Linear key:
   - `kk/bc-57-restore-lineargithub-delivery-pipeline`
   - `codex/bc-73-services-mode-parity`
7. Include the Linear key in PR titles and bodies so Linear auto-links PRs.
8. Use `Refs` when a PR advances but does not fully complete an issue.
9. Use `Closes` only when the acceptance criteria are actually satisfied.

## Labels

Use these Linear labels consistently:

- `repo:spektorAI`
- `kind:docs`
- `kind:ops`
- `kind:qa`
- `kind:feature`
- `priority:p0`
- `priority:p1`
- `priority:p2`
- `agent:ready`
- `agent:review`
- `status:blocked`

GitHub labels are optional for now. GitHub issue bodies should carry enough
context, acceptance criteria, and verification commands to stand alone.

## Acceptance Criteria

Every GitHub and Linear issue should include:

- Context: why this matters now.
- Scope: what should change.
- Acceptance criteria: observable outcomes.
- Verification: exact commands, smoke tests, or manual checks.
- Source: `ROADMAP.md` phase or prior issue link.

## Verification Defaults

Use the smallest verification that proves the work:

- Python/unit work: `make test`
- Streamlit import/server health: `make smoke`
- Local app start: `make app`
- Service-mode run/smoke: `make services-run` / `make services-smoke`
- Roadmap registry changes: `python3 -m json.tool ops/roadmap/features.json`
- Markdown/checklist changes: `git diff --check`
- Service-mode work: add or update a docker-compose/service smoke before
  claiming parity.

## Initial Seed

The initial project seed created:

| GitHub | Linear | Title |
| --- | --- | --- |
| [#1](https://github.com/WalksWithASwagger/spektorAI/issues/1) | [BC-57](https://linear.app/bc-ai/issue/BC-57/restore-lineargithub-delivery-pipeline) | Restore Linear/GitHub delivery pipeline |
| [#2](https://github.com/WalksWithASwagger/spektorAI/issues/2) | [BC-58](https://linear.app/bc-ai/issue/BC-58/clean-repo-hygiene-and-add-current-status-handoff) | Clean repo hygiene and add current status handoff |
| [#3](https://github.com/WalksWithASwagger/spektorAI/issues/3) | [BC-63](https://linear.app/bc-ai/issue/BC-63/add-browser-level-streamlit-verification) | Add browser-level Streamlit verification |
| [#4](https://github.com/WalksWithASwagger/spektorAI/issues/4) | [BC-73](https://linear.app/bc-ai/issue/BC-73/bring-services-mode-to-pipeline-parity) | Bring services mode to pipeline parity |
| [#5](https://github.com/WalksWithASwagger/spektorAI/issues/5) | [BC-83](https://linear.app/bc-ai/issue/BC-83/make-long-runs-recoverable-and-retryable) | Make long runs recoverable and retryable |
| [#6](https://github.com/WalksWithASwagger/spektorAI/issues/6) | [BC-88](https://linear.app/bc-ai/issue/BC-88/add-profile-manifests-and-user-defined-personas) | Add profile manifests and user-defined personas |
| [#7](https://github.com/WalksWithASwagger/spektorAI/issues/7) | [BC-90](https://linear.app/bc-ai/issue/BC-90/add-source-receipts-and-editorial-eval-fixtures) | Add source receipts and editorial eval fixtures |
| [#8](https://github.com/WalksWithASwagger/spektorAI/issues/8) | [BC-91](https://linear.app/bc-ai/issue/BC-91/add-deployment-and-operations-commands) | Add deployment and operations commands |
