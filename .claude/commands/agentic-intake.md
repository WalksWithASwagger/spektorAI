# Agentic Intake

Use this command to turn a rough bug report or feature request into a complete GitHub issue and linked Linear issue.

## Usage

```text
/agentic-intake <repo> <rough request>
```

## Required Behavior

1. Identify the target repo and read `agentic/contract.json`.
2. Ask one clarifying question only when the repo or expected outcome is genuinely ambiguous.
3. Draft the GitHub issue with these exact sections:
   - `## Context`
   - `## Acceptance Criteria`
   - `## Tests/Evals`
   - `## Verification`
   - `## Agent Instructions`
   - `## Out of Scope`
   - `## Linear`
4. Acceptance criteria must be Markdown checkboxes.
5. Include the repo verification commands from `agentic/contract.json`.
6. Create or link the Linear issue in the configured team/project.
7. Create the GitHub issue and include the Linear key in the title, body, or first comment.
8. Run `python3 scripts/agentic/issue_lint.py` against the final issue body.
9. Apply `agent:ready` only if the issue linter passes.

## Issue Template

```markdown
## Context

<What was reported, why it matters, and relevant repo context.>

## Acceptance Criteria

- [ ] <Observable outcome 1>
- [ ] <Observable outcome 2>

## Tests/Evals

- <Regression test, smoke test, eval, or fixture that proves the change.>

## Verification

- `<repo verification command>`

## Agent Instructions

- Keep the diff scoped to this issue.
- Respect the repo's max diff limits.
- Open a PR only after verification passes.

## Out of Scope

- <Explicit non-goals and likely overreach.>

## Linear

- Team: `<team>`
- Project: `<project>`
- Issue: `<linear key or pending link>`
```
