"""Single source of truth for Streamlit session state.

Every key that anything in the UI reads is initialized here, so we never
have a ``.get()`` scattered somewhere blowing up on a fresh session. The
set is split into two buckets:

- **Settings** — user preferences that persist across runs within a session
  (profile, provider, model, generation flags). Not cleared by Clear Run.
- **Per-run** — outputs from the last pipeline invocation (transcription,
  wisdom, chapters, images, etc.). Cleared by ``clear_run()`` so the UI
  can reset between uploads without a full page reload.
"""

from __future__ import annotations

from typing import Any, Dict

import streamlit as st

from whisperforge_core import images as images_mod

# --- Settings keys (preserved across runs) --------------------------------
_SETTINGS_DEFAULTS: Dict[str, Any] = {
    "selected_user": None,                       # filled from prompts.list_users()[0]
    "ai_provider": "Anthropic",                  # Haiku 4.5 is the default recommendation
    "ai_model": "claude-haiku-4-5",
    "ai_model_by_provider": {},                  # per-provider last-used memory
    # Generation Settings (mirror the fields surfaced in the ⚙ More popover)
    "cleanup_enabled": True,
    "chapters_enabled": True,
    "agentic_drafting": False,
    "fact_check_enabled": False,
    "images_enabled": False,
    "image_style": None,                         # None = use images.default_style()
    "image_aspect": "16:9",
    "image_model": "gemini-2.5-flash-image",
    # Dialog open-state — streamlit modals can't auto-open but we track this
    # for our own animations/toasts.
    "_dialog_open": None,
}

# --- Per-run keys (zeroed by clear_run) -----------------------------------
_PER_RUN_DEFAULTS: Dict[str, Any] = {
    # Input
    "pending_input": None,                       # {"source": "upload"|"record"|"paste", "payload": ..., "filename": str}
    "audio_file": None,                          # kept for Notion bundle compat
    # ASR outputs
    "transcription": "",
    "transcription_segments": [],
    # Pipeline outputs
    "wisdom": "",
    "outline": "",
    "social_content": "",
    "image_prompts": "",
    "article": "",
    "chapters": [],
    "cleaned_transcript": None,
    "article_critique": None,
    "fact_check_flags": [],
    "fact_check_ran": False,
    "generated_images": [],
    # Progress state (drives sac.steps + st.status)
    "pipeline_stage_idx": 0,                     # 0..7 where 7 = done
    "pipeline_stage_label": "",
    "pipeline_running": False,
    # Last Notion URL for the toast + history link display
    "last_notion_url": None,
}


def init_all_state() -> None:
    """Idempotently set every known key to its default if missing. Called
    once at the top of ``main()`` before any widget renders."""
    for k, default in _SETTINGS_DEFAULTS.items():
        st.session_state.setdefault(k, default)
    for k, default in _PER_RUN_DEFAULTS.items():
        st.session_state.setdefault(k, default)

    # Default image style resolves lazily the first time we need it — avoids
    # loading the YAML at import time when it's not used.
    if st.session_state.image_style is None:
        try:
            st.session_state.image_style = images_mod.default_style()
        except Exception:
            st.session_state.image_style = "kk"


def clear_run() -> None:
    """Zero every per-run key. Settings survive. Called by the bottom-bar
    Clear Run button so Kris can restart a run without losing his provider
    or image style."""
    for k, default in _PER_RUN_DEFAULTS.items():
        # Deep-copy mutable defaults so multiple clears don't share refs.
        if isinstance(default, (list, dict)):
            st.session_state[k] = type(default)()
        else:
            st.session_state[k] = default


def has_output() -> bool:
    """True when there's anything worth rendering in the Output card."""
    s = st.session_state
    return bool(
        s.get("wisdom")
        or s.get("article")
        or s.get("generated_images")
    )


def remember_model_for_provider(provider: str, model: str) -> None:
    """Persist the chosen model per provider so switching providers and
    back doesn't reset to the first option. Called by the sidebar model
    selectbox's on_change."""
    by = st.session_state.setdefault("ai_model_by_provider", {})
    by[provider] = model


def recall_model_for_provider(provider: str, fallback: str) -> str:
    """Return the last-used model for this provider, else ``fallback``."""
    return (st.session_state.get("ai_model_by_provider") or {}).get(provider, fallback)
