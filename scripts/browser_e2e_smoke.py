#!/usr/bin/env python3
"""Browser-level smoke for the primary WhisperForge loop.

This script boots Streamlit on a temporary port, drives the app with Playwright,
and validates that a seeded run can be reopened and exported from the real UI.

Requirements:
- `playwright` Python package
- Chromium installed for Playwright (`playwright install chromium`)
"""

from __future__ import annotations

import json
import os
import re
import signal
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent.parent
PORT = int(os.getenv("BROWSER_E2E_PORT", "8602"))
BASE_URL = f"http://127.0.0.1:{PORT}"
HEALTH_URL = f"{BASE_URL}/_stcore/health"


def _wait_for_health(url: str, timeout_s: float = 90.0) -> None:
    deadline = time.time() + timeout_s
    last_error: str | None = None
    while time.time() < deadline:
        try:
            response = requests.get(url, timeout=2.0)
            if response.ok:
                return
            last_error = f"HTTP {response.status_code}"
        except Exception as exc:  # pragma: no cover - network race
            last_error = str(exc)
        time.sleep(0.5)
    raise RuntimeError(f"Streamlit health check did not pass: {last_error}")


def _start_streamlit(cache_dir: Path) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env.setdefault("OPENAI_API_KEY", "dummy")
    env.setdefault("ANTHROPIC_API_KEY", "dummy")
    env.setdefault("NOTION_API_KEY", "dummy")
    env.setdefault("NOTION_DATABASE_ID", "dummy")
    env.setdefault("SERVICE_TOKEN", "dummy")
    env.setdefault("STREAMLIT_SERVER_FILE_WATCHER_TYPE", "none")
    env.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
    env["WHISPERFORGE_CACHE_DIR"] = str(cache_dir)
    cmd = [
        str(ROOT / "venv/bin/python"),
        "-m",
        "streamlit",
        "run",
        "app.py",
        "--server.headless",
        "true",
        "--server.port",
        str(PORT),
    ]
    return subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _seeded_run_manifest() -> tuple[str, dict[str, Any]]:
    runs_dir = ROOT / ".cache" / "runs"
    manifests = sorted(runs_dir.glob("*/manifest.json"), key=lambda p: p.stat().st_mtime)
    if not manifests:
        raise AssertionError("No seeded run manifests found under .cache/runs.")
    for path in reversed(manifests):
        data = json.loads(path.read_text())
        stage_names = [stage.get("stage") for stage in data.get("stages", [])]
        if "session_output" in stage_names:
            return path.parent.name, data
    raise AssertionError("No completed seeded run with session_output found.")


def _run_browser_flow() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Playwright is not installed. Run `pip install playwright` and "
            "`playwright install chromium`."
        ) from exc

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(BASE_URL, wait_until="domcontentloaded")

        page.get_by_role("button", name=re.compile("Runs")).click()
        page.get_by_label("Run to reopen").wait_for(timeout=60_000)
        page.get_by_role("button", name="Reopen output").click()
        page.wait_for_timeout(1_000)
        page.keyboard.press("Escape")
        markdown = page.get_by_role("button", name=re.compile("Markdown"))
        markdown.wait_for(timeout=60_000)
        markdown.click()
        page.get_by_role("button", name=re.compile("Download markdown")).wait_for(timeout=60_000)

        browser.close()


def main() -> int:
    seeded_run_id, before = _seeded_run_manifest()
    before_markdown = [item for item in before.get("exports", []) if item.get("kind") == "markdown"]
    before_latest_stamp = (before_markdown[-1] or {}).get("updated_at") if before_markdown else None
    work_cache = Path(tempfile.mkdtemp(prefix="whisperforge-browser-e2e-"))
    source_run = ROOT / ".cache" / "runs" / seeded_run_id
    target_run = work_cache / "runs" / seeded_run_id
    target_run.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_run, target_run, dirs_exist_ok=True)

    process = _start_streamlit(work_cache)
    try:
        _wait_for_health(HEALTH_URL)
        _run_browser_flow()
        manifest = json.loads(
            (work_cache / "runs" / seeded_run_id / "manifest.json").read_text()
        )
        after_markdown = [item for item in manifest.get("exports", []) if item.get("kind") == "markdown"]
        if not after_markdown:
            raise AssertionError(
                f"Expected at least one markdown export for run {seeded_run_id}."
            )
        markdown_count_grew = len(after_markdown) > len(before_markdown)
        latest_stamp_changed = (after_markdown[-1] or {}).get("updated_at") != before_latest_stamp
        if not markdown_count_grew and not latest_stamp_changed:
            raise AssertionError(
                f"Expected markdown export evidence to change for run {seeded_run_id}."
            )
        print("browser-e2e: OK")
        return 0
    except Exception as exc:
        print(f"browser-e2e: FAILED: {exc}", file=sys.stderr)
        return 1
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        shutil.rmtree(work_cache, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
