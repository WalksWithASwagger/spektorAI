#!/usr/bin/env python3
"""Fresh-run browser smoke for the primary WhisperForge demo loop.

Covers what ``browser_e2e_smoke.py`` does not: the full first-time path of
paste -> recipe pick -> run pipeline -> review tab -> markdown export, in a
real Chromium driven by Playwright, against a real Streamlit subprocess.

The smoke uses recorded fixture payloads by setting
``WHISPERFORGE_E2E_FIXTURE_PATH`` so no live provider credentials or network
writes are required.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "browser_e2e_fresh_run.json"
def _pick_port() -> int:
    explicit = os.getenv("BROWSER_E2E_FRESH_PORT")
    if explicit:
        return int(explicit)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


PORT = _pick_port()
BASE_URL = f"http://127.0.0.1:{PORT}"
HEALTH_URL = f"{BASE_URL}/_stcore/health"

TRANSCRIPT = (
    "Fresh-run browser E2E transcript from Wispr Flow. We are testing the "
    "full paste, recipe, run, review, and markdown export loop end to end."
)


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
    env["WHISPERFORGE_E2E_FIXTURE_PATH"] = str(FIXTURE_PATH)
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


def _latest_run_manifest(cache_dir: Path) -> tuple[str, dict]:
    runs_dir = cache_dir / "runs"
    manifests = sorted(
        runs_dir.glob("*/manifest.json"), key=lambda p: p.stat().st_mtime
    )
    if not manifests:
        raise AssertionError(f"No run manifests written under {runs_dir}.")
    path = manifests[-1]
    return path.parent.name, json.loads(path.read_text())


def _run_browser_flow(cache_dir: Path) -> str:
    try:
        from playwright.sync_api import expect, sync_playwright
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Playwright is not installed. Run `pip install playwright` and "
            "`playwright install chromium`."
        ) from exc

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(60_000)
        page.goto(BASE_URL, wait_until="domcontentloaded")

        # 1. Open the Paste tab and drop in a Wispr Flow transcript.
        page.get_by_role("tab", name=re.compile("Paste")).click()
        page.get_by_placeholder(
            "Drop in a Wispr Flow dictation, transcript, or some notes..."
        ).fill(TRANSCRIPT)
        page.keyboard.press("Tab")
        page.wait_for_timeout(500)

        # 2. Pick a recipe from the command palette. Streamlit selectbox is
        #    opaque to role-based selectors, so target by its label.
        recipe_picker = page.get_by_label("Command palette")
        recipe_picker.click()
        # The format_func renders the recipe name. "Article with receipts"
        # is the first non-manual recipe and the closest fit for the demo.
        page.get_by_text("Article with receipts", exact=True).click()

        # 3. Trigger the pipeline. The button label flips to "Run recipe"
        #    once a recipe is selected.
        run_button = page.get_by_role("button", name=re.compile("Run recipe")).first
        expect(run_button).to_be_enabled(timeout=30_000)
        run_button.click()

        # 4. Wait for the post-run tabs to appear and assert the article is
        #    visible inside the Article tab (the Review tab also renders an
        #    article preview, so scope strictly to one tabpanel).
        article_tab = page.get_by_role("tab", name=re.compile("Article"))
        article_tab.wait_for(state="visible", timeout=120_000)
        article_tab.click()
        article_panel = page.get_by_role("tabpanel").filter(
            has_text="Fresh-run E2E smoke article"
        ).first
        article_panel.wait_for(timeout=30_000)

        # 5. Switch to the Review tab and assert scorecard surfaces render.
        review_tab = page.get_by_role("tab", name=re.compile("Review"))
        review_tab.wait_for(state="visible", timeout=30_000)
        review_tab.click()
        page.get_by_text(re.compile("Verdict|Score|Receipts", re.I)).first.wait_for(
            timeout=30_000
        )

        # 6. Trigger the markdown export from the notion-save bar.
        markdown_button = page.get_by_role(
            "button", name=re.compile("Markdown")
        ).first
        markdown_button.wait_for(timeout=30_000)
        markdown_button.click()

        # 7. Wait for the manifest to record the markdown export.
        run_id = _wait_for_markdown_export(cache_dir, timeout_s=60.0)

        browser.close()
        return run_id


def _wait_for_markdown_export(cache_dir: Path, timeout_s: float) -> str:
    deadline = time.time() + timeout_s
    last_run_id: str | None = None
    while time.time() < deadline:
        try:
            run_id, manifest = _latest_run_manifest(cache_dir)
            last_run_id = run_id
            exports = manifest.get("exports", [])
            for item in exports:
                if item.get("kind") != "markdown":
                    continue
                value = item.get("value")
                if value and Path(value).exists():
                    return run_id
        except AssertionError:
            pass
        time.sleep(0.5)
    raise AssertionError(
        f"Markdown export did not land on disk within {timeout_s:.0f}s "
        f"(last run id: {last_run_id})."
    )


def main() -> int:
    if not FIXTURE_PATH.exists():
        print(
            f"browser-e2e-fresh: FAILED: missing fixture file {FIXTURE_PATH}",
            file=sys.stderr,
        )
        return 1
    work_cache = Path(tempfile.mkdtemp(prefix="whisperforge-fresh-e2e-"))
    process = _start_streamlit(work_cache)
    try:
        _wait_for_health(HEALTH_URL)
        run_id = _run_browser_flow(work_cache)

        manifest = json.loads(
            (work_cache / "runs" / run_id / "manifest.json").read_text()
        )
        recipe = manifest.get("metadata", {}).get("recipe", {})
        if recipe.get("recipe_id") != "article_with_receipts":
            raise AssertionError(
                f"Expected recipe 'article_with_receipts' on run {run_id}, "
                f"got {recipe!r}."
            )
        stages = [stage.get("stage") for stage in manifest.get("stages", [])]
        if "session_output" not in stages:
            raise AssertionError(
                f"Run {run_id} did not record a session_output stage "
                f"(stages: {stages})."
            )
        print(f"browser-e2e-fresh: OK (run {run_id})")
        return 0
    except Exception as exc:
        print(f"browser-e2e-fresh: FAILED: {exc}", file=sys.stderr)
        if process.poll() is None:
            try:
                # Drain a bit of stdout to make the failure easier to debug.
                process.send_signal(signal.SIGTERM)
                out, _ = process.communicate(timeout=10)
                if out:
                    tail = "\n".join(out.splitlines()[-40:])
                    print(f"--- streamlit tail ---\n{tail}", file=sys.stderr)
            except subprocess.TimeoutExpired:
                process.kill()
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
