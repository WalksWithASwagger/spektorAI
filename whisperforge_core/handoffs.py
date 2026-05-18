"""Agent-ready handoff draft rendering and persistence."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

from . import run_artifacts

REQUIRED_SECTIONS = [
    "Context",
    "Acceptance Criteria",
    "Tests/Evals",
    "Verification",
    "Agent Instructions",
    "Out of Scope",
]


@dataclass
class HandoffDraft:
    title: str
    body: str
    source_kind: str
    source_title: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_issue_draft(
    *,
    title: str,
    source_text: str,
    source_kind: str = "output",
    source_title: str = "",
    recipe: Mapping[str, Any] | None = None,
    scorecard: Mapping[str, Any] | None = None,
    verification: list[str] | None = None,
) -> HandoffDraft:
    recipe = recipe or {}
    scorecard = scorecard or {}
    verification = verification or ["make test", "git diff --check"]
    source_excerpt = _excerpt(source_text)
    body = "\n\n".join([
        "## Context\n\n"
        f"Drafted from WhisperForge {source_kind}: {source_title or title}.\n\n"
        f"Source excerpt:\n\n> {source_excerpt}",
        "## Acceptance Criteria\n\n"
        "- [ ] Confirm the requested outcome against the source excerpt.\n"
        "- [ ] Implement or route the smallest useful next step.\n"
        "- [ ] Preserve source receipts, scorecard notes, and handoff context.\n"
        "- [ ] Leave external tracker creation to an explicit user action.",
        "## Tests/Evals\n\n"
        "- Add or update unit tests for changed behavior.\n"
        "- Run any credential-free evals that cover the handoff path.\n"
        "- Re-run issue lint before marking the draft agent-ready.",
        "## Verification\n\n" + "\n".join(f"- `{command}`" for command in verification),
        "## Agent Instructions\n\n"
        "Use the source excerpt as the primary brief. Keep the diff scoped, "
        "call out uncertainty instead of inventing details, and do not create "
        "GitHub or Linear records unless the user explicitly confirms that action.\n\n"
        f"Recipe: {recipe.get('recipe_name') or recipe.get('name') or recipe.get('recipe_id') or 'manual'}\n\n"
        f"Scorecard: {scorecard.get('verdict_label') or 'not available'} "
        f"({scorecard.get('average_score', 'n/a')}/100)",
        "## Out of Scope\n\n"
        "- Automatic GitHub or Linear issue creation.\n"
        "- Broad refactors unrelated to the brief.\n"
        "- Publishing or notifying external people without confirmation.",
    ])
    return HandoffDraft(
        title=title.strip() or "WhisperForge handoff",
        body=body + "\n",
        source_kind=source_kind,
        source_title=source_title,
        metadata={
            "required_sections": list(REQUIRED_SECTIONS),
            "recipe": dict(recipe),
            "scorecard": dict(scorecard),
        },
    )


def persist_draft(run_id: str, draft: HandoffDraft) -> Path:
    path = run_artifacts.run_dir(run_id) / "handoffs" / f"{_slug(draft.title)}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {draft.title}\n\n{draft.body}", encoding="utf-8")
    run_artifacts.write_stage(
        run_id,
        "handoff_draft",
        {**draft.to_dict(), "path": str(path)},
    )
    run_artifacts.record_export(run_id, "handoff_draft", str(path))
    return path


def _excerpt(text: str, limit: int = 900) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if not cleaned:
        return "No source text was available. Review the current run artifacts before implementation."
    return cleaned[:limit] + ("..." if len(cleaned) > limit else "")


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.lower()).strip(".-")
    return slug[:80] or "handoff-draft"
