"""Approval-gated GitHub / Linear issue creation for handoff drafts.

The UI renders a preview (built by :mod:`whisperforge_core.handoffs`) and only
calls into here when the user clicks "Approve and create". Anything that
short-circuits the external call - missing config, explicit dry-run flag, the
env override - surfaces visibly through :class:`HandoffResult` so the UI can
say *why* the API call didn't go out instead of silently faking success.

Three layers gate the actual network call, evaluated in order:
1. ``WHISPERFORGE_HANDOFF_DRY_RUN=1`` env override (kill switch for tests / demos).
2. The ``dry_run`` argument from the caller.
3. Missing config for the target (``gh`` CLI absent / ``LINEAR_API_KEY`` unset).

For GitHub we shell out to the ``gh`` CLI to avoid a new auth surface - it's
already on every dev machine and inherits the existing token. For Linear we hit
the GraphQL endpoint directly with ``requests`` (no new dep). Labels for Linear
must be passed as IDs in this v1; name-based labels would need an extra
``issueLabels`` query and we'd rather keep the surface small.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Optional

import requests

from .logging import get_logger

logger = get_logger("handoff_router")

LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"
_TIMEOUT = 30


@dataclass
class HandoffResult:
    success: bool
    target: str
    url: Optional[str] = None
    error: Optional[str] = None
    dry_run: bool = False
    details: dict = field(default_factory=dict)


def _force_dry_run() -> bool:
    return os.getenv("WHISPERFORGE_HANDOFF_DRY_RUN", "").strip() in {"1", "true", "yes"}


def routing_available() -> dict[str, bool]:
    """Report whether each target has the config it needs to actually fire.

    Used by the UI to label the approval button and to disable targets that
    will only ever produce a dry-run result.
    """
    github_ok = shutil.which("gh") is not None and bool(
        os.getenv("WHISPERFORGE_HANDOFF_GITHUB_REPO")
    )
    linear_ok = bool(os.getenv("LINEAR_API_KEY")) and bool(
        os.getenv("WHISPERFORGE_HANDOFF_LINEAR_TEAM_ID")
    )
    return {"github": github_ok, "linear": linear_ok}


def create_github_issue(
    *,
    repo: str,
    title: str,
    body: str,
    labels: Optional[list[str]] = None,
    dry_run: bool = False,
) -> HandoffResult:
    labels = labels or []
    if _force_dry_run() or dry_run:
        return HandoffResult(success=True, target="github", dry_run=True)
    if not shutil.which("gh"):
        return HandoffResult(
            success=False,
            target="github",
            dry_run=True,
            error="gh CLI not found on PATH; left as dry-run.",
        )
    if not repo:
        return HandoffResult(
            success=False,
            target="github",
            error="No GitHub repo configured (set WHISPERFORGE_HANDOFF_GITHUB_REPO or pass repo).",
        )

    cmd = ["gh", "issue", "create", "--repo", repo, "--title", title, "--body", body]
    if labels:
        cmd += ["--label", ",".join(labels)]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=_TIMEOUT, check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("gh issue create failed: %s", exc)
        return HandoffResult(success=False, target="github", error=str(exc))

    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "gh exited non-zero").strip()
        return HandoffResult(success=False, target="github", error=err)

    url = _extract_github_url(proc.stdout)
    if not url:
        return HandoffResult(
            success=False,
            target="github",
            error=f"gh succeeded but no URL parsed from output: {proc.stdout[:200]!r}",
        )
    return HandoffResult(success=True, target="github", url=url)


def create_linear_issue(
    *,
    team_id: str,
    title: str,
    description: str,
    label_ids: Optional[list[str]] = None,
    dry_run: bool = False,
    api_key: Optional[str] = None,
) -> HandoffResult:
    label_ids = label_ids or []
    if _force_dry_run() or dry_run:
        return HandoffResult(success=True, target="linear", dry_run=True)
    key = api_key or os.getenv("LINEAR_API_KEY")
    if not key:
        return HandoffResult(
            success=False,
            target="linear",
            dry_run=True,
            error="LINEAR_API_KEY not set; left as dry-run.",
        )
    if not team_id:
        return HandoffResult(
            success=False,
            target="linear",
            error="No Linear team_id configured (set WHISPERFORGE_HANDOFF_LINEAR_TEAM_ID or pass team_id).",
        )

    mutation = (
        "mutation IssueCreate($input: IssueCreateInput!) {"
        "  issueCreate(input: $input) {"
        "    success"
        "    issue { id identifier url }"
        "  }"
        "}"
    )
    variables = {
        "input": {
            "teamId": team_id,
            "title": title,
            "description": description,
        }
    }
    if label_ids:
        variables["input"]["labelIds"] = list(label_ids)

    try:
        resp = requests.post(
            LINEAR_GRAPHQL_URL,
            headers={"Authorization": key, "Content-Type": "application/json"},
            json={"query": mutation, "variables": variables},
            timeout=_TIMEOUT,
        )
    except requests.RequestException as exc:
        logger.warning("Linear request failed: %s", exc)
        return HandoffResult(success=False, target="linear", error=str(exc))

    if resp.status_code >= 400:
        return HandoffResult(
            success=False,
            target="linear",
            error=f"Linear HTTP {resp.status_code}: {resp.text[:300]}",
        )
    try:
        data = resp.json()
    except ValueError as exc:
        return HandoffResult(success=False, target="linear", error=f"Linear returned non-JSON: {exc}")

    if data.get("errors"):
        msg = "; ".join(err.get("message", "") for err in data["errors"]) or "Linear GraphQL error"
        return HandoffResult(success=False, target="linear", error=msg)

    payload = (((data.get("data") or {}).get("issueCreate")) or {})
    if not payload.get("success"):
        return HandoffResult(
            success=False,
            target="linear",
            error="Linear reported success=false on issueCreate.",
        )
    issue = payload.get("issue") or {}
    url = issue.get("url")
    if not url:
        return HandoffResult(
            success=False,
            target="linear",
            error="Linear returned no issue URL.",
            details={"issue": issue},
        )
    return HandoffResult(
        success=True,
        target="linear",
        url=url,
        details={"identifier": issue.get("identifier")},
    )


def _extract_github_url(stdout: str) -> Optional[str]:
    # `gh issue create` prints the URL on its own line (sometimes after a
    # "Creating issue in ..." banner). Take the last https URL we see.
    for line in reversed((stdout or "").splitlines()):
        line = line.strip()
        if line.startswith("https://"):
            return line
    return None
