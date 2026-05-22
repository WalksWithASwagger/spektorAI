"""Tests for the approval-gated handoff router.

We never let real subprocess / HTTP calls escape these tests - everything is
either intercepted or short-circuited via the dry-run gate. The router is the
only thing standing between a user click and a real GitHub/Linear write, so
the gate behavior is what we check hardest.
"""

import subprocess

import pytest

from whisperforge_core import handoff_router


# --- GitHub --------------------------------------------------------------


def test_github_dry_run_skips_subprocess(monkeypatch):
    called = []

    def boom(*args, **kwargs):
        called.append(args)
        raise AssertionError("subprocess.run must not be called in dry-run")

    monkeypatch.setattr(handoff_router.subprocess, "run", boom)
    monkeypatch.delenv("WHISPERFORGE_HANDOFF_DRY_RUN", raising=False)

    result = handoff_router.create_github_issue(
        repo="owner/repo", title="t", body="b", dry_run=True,
    )

    assert result.success is True
    assert result.dry_run is True
    assert result.url is None
    assert called == []


def test_github_env_kill_switch_forces_dry_run_even_when_caller_asks_for_real(monkeypatch):
    monkeypatch.setenv("WHISPERFORGE_HANDOFF_DRY_RUN", "1")

    def boom(*args, **kwargs):
        raise AssertionError("kill switch must short-circuit subprocess.run")

    monkeypatch.setattr(handoff_router.subprocess, "run", boom)

    result = handoff_router.create_github_issue(
        repo="owner/repo", title="t", body="b", dry_run=False,
    )

    assert result.success is True
    assert result.dry_run is True


def test_github_success_parses_url_from_stdout(monkeypatch):
    monkeypatch.delenv("WHISPERFORGE_HANDOFF_DRY_RUN", raising=False)
    monkeypatch.setattr(handoff_router.shutil, "which", lambda _: "/usr/bin/gh")

    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="Creating issue in owner/repo\nhttps://github.com/owner/repo/issues/42\n",
            stderr="",
        )

    monkeypatch.setattr(handoff_router.subprocess, "run", fake_run)

    result = handoff_router.create_github_issue(
        repo="owner/repo",
        title="Title",
        body="Body",
        labels=["agent:ready", "handoff"],
        dry_run=False,
    )

    assert result.success is True
    assert result.dry_run is False
    assert result.url == "https://github.com/owner/repo/issues/42"
    assert result.target == "github"
    assert "--repo" in captured["cmd"]
    assert "owner/repo" in captured["cmd"]
    assert "--label" in captured["cmd"]
    assert "agent:ready,handoff" in captured["cmd"]


def test_github_nonzero_returncode_surfaces_error(monkeypatch):
    monkeypatch.delenv("WHISPERFORGE_HANDOFF_DRY_RUN", raising=False)
    monkeypatch.setattr(handoff_router.shutil, "which", lambda _: "/usr/bin/gh")

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=1,
            stdout="",
            stderr="error: HTTP 401 Bad credentials\n",
        )

    monkeypatch.setattr(handoff_router.subprocess, "run", fake_run)

    result = handoff_router.create_github_issue(
        repo="owner/repo", title="t", body="b", dry_run=False,
    )

    assert result.success is False
    assert result.dry_run is False
    assert "401" in (result.error or "")


def test_github_missing_gh_cli_returns_dry_run_with_error(monkeypatch):
    monkeypatch.delenv("WHISPERFORGE_HANDOFF_DRY_RUN", raising=False)
    monkeypatch.setattr(handoff_router.shutil, "which", lambda _: None)

    def boom(*args, **kwargs):
        raise AssertionError("must not run subprocess when gh missing")

    monkeypatch.setattr(handoff_router.subprocess, "run", boom)

    result = handoff_router.create_github_issue(
        repo="owner/repo", title="t", body="b", dry_run=False,
    )

    assert result.success is False
    assert result.dry_run is True
    assert "gh CLI" in (result.error or "")


# --- Linear --------------------------------------------------------------


def test_linear_dry_run_skips_http_call(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("requests.post must not be called in dry-run")

    monkeypatch.setattr(handoff_router.requests, "post", boom)
    monkeypatch.delenv("WHISPERFORGE_HANDOFF_DRY_RUN", raising=False)

    result = handoff_router.create_linear_issue(
        team_id="team-1", title="t", description="d", dry_run=True, api_key="key",
    )

    assert result.success is True
    assert result.dry_run is True


def test_linear_missing_api_key_returns_dry_run_with_error(monkeypatch):
    monkeypatch.delenv("LINEAR_API_KEY", raising=False)
    monkeypatch.delenv("WHISPERFORGE_HANDOFF_DRY_RUN", raising=False)

    def boom(*args, **kwargs):
        raise AssertionError("must not call requests when key missing")

    monkeypatch.setattr(handoff_router.requests, "post", boom)

    result = handoff_router.create_linear_issue(
        team_id="team-1", title="t", description="d", dry_run=False,
    )

    assert result.success is False
    assert result.dry_run is True
    assert "LINEAR_API_KEY" in (result.error or "")


class _FakeResp:
    def __init__(self, payload, status_code=200, text=""):
        self._payload = payload
        self.status_code = status_code
        self.text = text or str(payload)

    def json(self):
        return self._payload


def test_linear_success_returns_issue_url(monkeypatch):
    monkeypatch.delenv("WHISPERFORGE_HANDOFF_DRY_RUN", raising=False)

    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return _FakeResp({
            "data": {
                "issueCreate": {
                    "success": True,
                    "issue": {
                        "id": "issue-uuid",
                        "identifier": "ENG-123",
                        "url": "https://linear.app/team/issue/ENG-123/title",
                    },
                }
            }
        })

    monkeypatch.setattr(handoff_router.requests, "post", fake_post)

    result = handoff_router.create_linear_issue(
        team_id="team-uuid",
        title="Title",
        description="Description body",
        label_ids=["label-1"],
        dry_run=False,
        api_key="lin_api_xxx",
    )

    assert result.success is True
    assert result.dry_run is False
    assert result.url == "https://linear.app/team/issue/ENG-123/title"
    assert result.details.get("identifier") == "ENG-123"
    assert captured["url"] == handoff_router.LINEAR_GRAPHQL_URL
    assert captured["headers"]["Authorization"] == "lin_api_xxx"
    assert captured["json"]["variables"]["input"]["teamId"] == "team-uuid"
    assert captured["json"]["variables"]["input"]["labelIds"] == ["label-1"]


def test_linear_http_401_returns_failure(monkeypatch):
    monkeypatch.delenv("WHISPERFORGE_HANDOFF_DRY_RUN", raising=False)

    def fake_post(*args, **kwargs):
        return _FakeResp({}, status_code=401, text="unauthenticated")

    monkeypatch.setattr(handoff_router.requests, "post", fake_post)

    result = handoff_router.create_linear_issue(
        team_id="team-uuid", title="t", description="d",
        dry_run=False, api_key="bad",
    )

    assert result.success is False
    assert result.dry_run is False
    assert "401" in (result.error or "")


def test_linear_graphql_errors_surface(monkeypatch):
    monkeypatch.delenv("WHISPERFORGE_HANDOFF_DRY_RUN", raising=False)

    def fake_post(*args, **kwargs):
        return _FakeResp({"errors": [{"message": "Team not found"}]})

    monkeypatch.setattr(handoff_router.requests, "post", fake_post)

    result = handoff_router.create_linear_issue(
        team_id="team-uuid", title="t", description="d",
        dry_run=False, api_key="key",
    )

    assert result.success is False
    assert "Team not found" in (result.error or "")


def test_linear_success_false_in_payload_surfaces_failure(monkeypatch):
    monkeypatch.delenv("WHISPERFORGE_HANDOFF_DRY_RUN", raising=False)

    def fake_post(*args, **kwargs):
        return _FakeResp({"data": {"issueCreate": {"success": False, "issue": None}}})

    monkeypatch.setattr(handoff_router.requests, "post", fake_post)

    result = handoff_router.create_linear_issue(
        team_id="team-uuid", title="t", description="d",
        dry_run=False, api_key="key",
    )

    assert result.success is False
    assert "success=false" in (result.error or "")


# --- routing_available ---------------------------------------------------


def test_routing_available_reports_both_off_when_unconfigured(monkeypatch):
    monkeypatch.setattr(handoff_router.shutil, "which", lambda _: None)
    monkeypatch.delenv("WHISPERFORGE_HANDOFF_GITHUB_REPO", raising=False)
    monkeypatch.delenv("LINEAR_API_KEY", raising=False)
    monkeypatch.delenv("WHISPERFORGE_HANDOFF_LINEAR_TEAM_ID", raising=False)
    monkeypatch.delenv("WHISPERFORGE_HANDOFF_FOLLOWUP_QUEUE_PATH", raising=False)
    monkeypatch.delenv("WHISPERFORGE_HANDOFF_NOTION_DRAFT_DIR", raising=False)

    assert handoff_router.routing_available() == {
        "github": False,
        "linear": False,
        "followup_queue": False,
        "notion_page_draft": False,
        "notion_task_draft": False,
    }


def test_routing_available_detects_both_on_when_configured(monkeypatch):
    monkeypatch.setattr(handoff_router.shutil, "which", lambda _: "/usr/bin/gh")
    monkeypatch.setenv("WHISPERFORGE_HANDOFF_GITHUB_REPO", "owner/repo")
    monkeypatch.setenv("LINEAR_API_KEY", "key")
    monkeypatch.setenv("WHISPERFORGE_HANDOFF_LINEAR_TEAM_ID", "team-uuid")
    monkeypatch.setenv("WHISPERFORGE_HANDOFF_FOLLOWUP_QUEUE_PATH", "/tmp/followups.jsonl")
    monkeypatch.setenv("WHISPERFORGE_HANDOFF_NOTION_DRAFT_DIR", "/tmp/notion-drafts")

    assert handoff_router.routing_available() == {
        "github": True,
        "linear": True,
        "followup_queue": True,
        "notion_page_draft": True,
        "notion_task_draft": True,
    }


# --- Follow-up queue ------------------------------------------------------


def test_followup_queue_dry_run_skips_file_write(monkeypatch, tmp_path):
    queue_path = tmp_path / "followups.jsonl"
    monkeypatch.delenv("WHISPERFORGE_HANDOFF_DRY_RUN", raising=False)

    result = handoff_router.create_followup_queue_item(
        queue_path=str(queue_path),
        title="Follow-up",
        body="Body",
        dry_run=True,
    )

    assert result.success is True
    assert result.dry_run is True
    assert not queue_path.exists()


def test_followup_queue_missing_path_returns_dry_run_with_error(monkeypatch):
    monkeypatch.delenv("WHISPERFORGE_HANDOFF_DRY_RUN", raising=False)

    result = handoff_router.create_followup_queue_item(
        queue_path="",
        title="Follow-up",
        body="Body",
        dry_run=False,
    )

    assert result.success is False
    assert result.dry_run is True
    assert "WHISPERFORGE_HANDOFF_FOLLOWUP_QUEUE_PATH" in (result.error or "")


def test_followup_queue_success_appends_jsonl(monkeypatch, tmp_path):
    queue_path = tmp_path / "followups.jsonl"
    monkeypatch.delenv("WHISPERFORGE_HANDOFF_DRY_RUN", raising=False)

    result = handoff_router.create_followup_queue_item(
        queue_path=str(queue_path),
        title="Follow-up title",
        body="Follow-up body",
        dry_run=False,
    )

    assert result.success is True
    assert result.dry_run is False
    assert queue_path.exists()
    lines = queue_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert "Follow-up title" in lines[0]
    assert result.url == queue_path.resolve().as_uri()


def test_followup_queue_write_failure_surfaces_error(monkeypatch, tmp_path):
    queue_path = tmp_path / "missing" / "followups.jsonl"
    monkeypatch.delenv("WHISPERFORGE_HANDOFF_DRY_RUN", raising=False)

    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(handoff_router.Path, "open", boom)

    result = handoff_router.create_followup_queue_item(
        queue_path=str(queue_path),
        title="Follow-up title",
        body="Follow-up body",
        dry_run=False,
    )

    assert result.success is False
    assert result.dry_run is False
    assert "disk full" in (result.error or "")


# --- Notion drafts --------------------------------------------------------


def test_notion_draft_dry_run_skips_file_write(monkeypatch, tmp_path):
    monkeypatch.delenv("WHISPERFORGE_HANDOFF_DRY_RUN", raising=False)

    result = handoff_router.create_notion_draft(
        draft_dir=str(tmp_path),
        title="Digest draft",
        body="Body",
        draft_type="page",
        dry_run=True,
    )

    assert result.success is True
    assert result.dry_run is True
    assert list(tmp_path.iterdir()) == []


def test_notion_draft_missing_dir_returns_dry_run_with_error(monkeypatch):
    monkeypatch.delenv("WHISPERFORGE_HANDOFF_DRY_RUN", raising=False)

    result = handoff_router.create_notion_draft(
        draft_dir="",
        title="Digest draft",
        body="Body",
        draft_type="task",
        dry_run=False,
    )

    assert result.success is False
    assert result.dry_run is True
    assert "WHISPERFORGE_HANDOFF_NOTION_DRAFT_DIR" in (result.error or "")


def test_notion_draft_success_writes_local_markdown(monkeypatch, tmp_path):
    monkeypatch.delenv("WHISPERFORGE_HANDOFF_DRY_RUN", raising=False)

    result = handoff_router.create_notion_draft(
        draft_dir=str(tmp_path),
        title="Digest follow-up",
        body="Digest body",
        draft_type="task",
        dry_run=False,
    )

    path = tmp_path / "digest-follow-up.task.md"
    assert result.success is True
    assert result.dry_run is False
    assert result.url == path.resolve().as_uri()
    assert result.details["draft_path"] == str(path)
    assert "draft_type: notion_task" in path.read_text(encoding="utf-8")
    assert "Digest body" in path.read_text(encoding="utf-8")
