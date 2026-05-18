# Linear/GitHub Delivery Pipeline

Last updated: 2026-05-18

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

Agentic delivery contract: [`agentic/contract.json`](../agentic/contract.json). v1 opens PRs only; humans remain the merge gate. Ready work uses `agent:ready`; `auto-implement` and `autonomous` are migration aliases.


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

GitHub labels are available for the active wave. Use `repo:spektorAI`,
`priority:p0` / `priority:p1` / `priority:p2`, and the most specific
`kind:*` label. Add `agent:ready` only when you intentionally want to trigger
the agentic dev loop.

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

## 2026 Master Plan Seed

The 2026 product reset lives in
[`WHISPERFORGE-MASTER-PLAN-2026-05-18.md`](WHISPERFORGE-MASTER-PLAN-2026-05-18.md).
The issue wave was created without the GitHub `agent:ready` label so the
external trackers can be reviewed before starting a swarm.

| GitHub | Linear | Title |
| --- | --- | --- |
| [#13](https://github.com/WalksWithASwagger/spektorAI/issues/13) | [BC-221](https://linear.app/bc-ai/issue/BC-221/build-wispr-flow-voice-inbox-and-capture-handoff) | Build Wispr Flow voice inbox and capture handoff |
| [#14](https://github.com/WalksWithASwagger/spektorAI/issues/14) | [BC-222](https://linear.app/bc-ai/issue/BC-222/add-knowledge-base-inventory-and-health-audit) | Add knowledge-base inventory and health audit |
| [#15](https://github.com/WalksWithASwagger/spektorAI/issues/15) | [BC-223](https://linear.app/bc-ai/issue/BC-223/add-source-grounded-retrieval-inspector) | Add source-grounded retrieval inspector |
| [#16](https://github.com/WalksWithASwagger/spektorAI/issues/16) | [BC-224](https://linear.app/bc-ai/issue/BC-224/add-prompt-recipe-manifests-and-command-palette) | Add prompt recipe manifests and command palette |
| [#17](https://github.com/WalksWithASwagger/spektorAI/issues/17) | [BC-226](https://linear.app/bc-ai/issue/BC-226/build-source-grounded-composition-studio) | Build source-grounded composition studio |
| [#18](https://github.com/WalksWithASwagger/spektorAI/issues/18) | [BC-225](https://linear.app/bc-ai/issue/BC-225/add-modern-transcription-provider-and-privacy-matrix) | Add modern transcription provider and privacy matrix |
| [#19](https://github.com/WalksWithASwagger/spektorAI/issues/19) | [BC-227](https://linear.app/bc-ai/issue/BC-227/add-voice-grounding-and-usefulness-scorecards) | Add voice, grounding, and usefulness scorecards |
| [#20](https://github.com/WalksWithASwagger/spektorAI/issues/20) | [BC-228](https://linear.app/bc-ai/issue/BC-228/create-agentic-handoff-exports-for-issues-and-follow-ups) | Create agentic handoff exports for issues and follow-ups |
| [#21](https://github.com/WalksWithASwagger/spektorAI/issues/21) | [BC-229](https://linear.app/bc-ai/issue/BC-229/add-run-artifact-reopen-resume-and-retry-ui) | Add run artifact reopen, resume, and retry UI |
| [#22](https://github.com/WalksWithASwagger/spektorAI/issues/22) | [BC-230](https://linear.app/bc-ai/issue/BC-230/upgrade-profiles-into-a-voiceproject-operating-system) | Upgrade profiles into a voice/project operating system |
| [#23](https://github.com/WalksWithASwagger/spektorAI/issues/23) | [BC-231](https://linear.app/bc-ai/issue/BC-231/add-resurfacing-digest-for-captures-and-generated-outputs) | Add resurfacing digest for captures and generated outputs |
| [#24](https://github.com/WalksWithASwagger/spektorAI/issues/24) | [BC-232](https://linear.app/bc-ai/issue/BC-232/prototype-songforge-lyric-and-prompt-pack-mode) | Prototype SongForge lyric and prompt-pack mode |
