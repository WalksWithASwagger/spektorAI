#!/usr/bin/env python3
"""Rendered Streamlit smoke test for the WhisperForge shell.

This uses Streamlit's built-in testing harness, so it stays dependency-light:
no browser driver, no API credentials, and no local server. It complements
``tests/smoke.sh``:

- ``tests/smoke.sh`` proves the server can boot and answer health checks.
- this script proves the app renders its main shell without Streamlit
  exceptions.
"""

from __future__ import annotations

import sys
import os
from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parent.parent


def _labels(items) -> list[str]:
    return [getattr(item, "label", "") for item in items]


def main() -> int:
    os.chdir(ROOT)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    os.environ.setdefault("WHISPERFORGE_DISCOVER_OLLAMA", "0")

    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20)
    app.run()

    if app.exception:
        for exc in app.exception:
            print(f"ui-smoke: Streamlit exception: {exc}", file=sys.stderr)
        return 1

    tab_labels = _labels(app.tabs)
    expected_tabs = {"📂 Upload", "🎙 Record", "✎ Paste"}
    missing_tabs = sorted(expected_tabs - set(tab_labels))
    if missing_tabs:
        print(
            f"ui-smoke: missing input tabs: {', '.join(missing_tabs)}",
            file=sys.stderr,
        )
        return 1

    if len(app.sidebar.selectbox) < 2:
        print(
            "ui-smoke: expected sidebar profile/model selectboxes",
            file=sys.stderr,
        )
        return 1

    markdown_text = "\n".join(str(item.value) for item in app.markdown)
    required_fragments = [
        "WhisperForge // Control_Center",
        "Input",
    ]
    for fragment in required_fragments:
        if fragment not in markdown_text:
            print(f"ui-smoke: missing rendered text: {fragment}", file=sys.stderr)
            return 1

    app.session_state["article"] = "# Draft\n\nA grounded composition draft."
    app.session_state["wisdom"] = "Source-grounded insight."
    app.session_state["transcription"] = "A source transcript with a useful quote."
    app.session_state["article_critique"] = "- tighten the ending"
    app.session_state["fact_check_ran"] = True
    app.session_state["fact_check_flags"] = [
        {"claim": "The sky is red", "issue": "The source says blue."}
    ]
    app.session_state["article_compare"] = "Alternate provider draft."
    app.session_state["compare_label"] = "alternate"
    app.session_state["persona_articles"] = [
        {"name": "Operator", "text": "Persona variant."}
    ]
    app.run()

    if app.exception:
        for exc in app.exception:
            print(f"ui-smoke: Streamlit exception after output seed: {exc}", file=sys.stderr)
        return 1

    output_tabs = set(_labels(app.tabs))
    for label in {"📝 Article", "🧭 Review"}:
        if label not in output_tabs:
            print(f"ui-smoke: missing output tab: {label}", file=sys.stderr)
            return 1

    print("ui-smoke: rendered shell OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
