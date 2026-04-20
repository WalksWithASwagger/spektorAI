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

import json
from typing import Any, Dict

import streamlit as st

from whisperforge_core import images as images_mod
from whisperforge_core import prompts as prompts_mod
from whisperforge_core.config import CACHE_DIR

# Where we remember which user profile was active last. Lives next to the
# other small caches so it gets cleaned up by `cache.clear()` if the user
# wants a fresh start.
_PREFERENCES_FILE = CACHE_DIR / "ui_preferences.json"

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
    # Article length target — fed into article_writing + article_revise.
    # "Brief": ~500 words, "Standard": ~1500, "Long-form": ~3000.
    "article_length": "Standard",
    # Auto-save to Notion when the pipeline finishes — restores the old
    # Record-tab "I'm Feeling Lucky" behavior as an opt-out toggle.
    "auto_save_notion": True,
    # KB retrieval mode: "auto" (engage RAG when KB has >25 chunks),
    # "always" (every call routes through top-K retrieval), or "never"
    # (legacy dump-entire-KB path; best for small KBs where Anthropic
    # prompt caching already wins).
    "rag_mode": "auto",
    # Also write a markdown export to .cache/exports/ whenever we save
    # to Notion. Useful for keeping a local / Obsidian-vault copy.
    "auto_export_markdown": False,
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


def _load_preferences() -> dict:
    """Read the persisted last-user-selection JSON. Empty dict on miss."""
    try:
        return json.loads(_PREFERENCES_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _save_preferences(prefs: dict) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _PREFERENCES_FILE.write_text(json.dumps(prefs))
    except OSError:
        pass  # non-critical


def _resolve_default_user() -> str:
    """Pick the right user to default to.

    Priority:
      1. Last user selected in this Streamlit deploy (persisted to disk).
      2. A user with a non-empty knowledge_base/ folder — without a KB,
         prompt caching can't engage and outputs aren't in-voice.
      3. Alphabetically first as final fallback.

    This fixes a 0.6.0 regression where the new sidebar always defaulted to
    the alphabetically first user (Caroline_Hilton in Kris's tree), which
    meant his actual KB never got injected and the cache stayed cold.
    """
    users = prompts_mod.list_users()
    if not users:
        return "default_user"
    # 1. Last-selected
    last = _load_preferences().get("selected_user")
    if last in users:
        return last
    # 2. First user with a non-empty KB
    for u in users:
        if prompts_mod.load_knowledge_base(u):
            return u
    # 3. Fallback
    return users[0]


def init_all_state() -> None:
    """Idempotently set every known key to its default if missing. Called
    once at the top of ``main()`` before any widget renders."""
    for k, default in _SETTINGS_DEFAULTS.items():
        st.session_state.setdefault(k, default)
    for k, default in _PER_RUN_DEFAULTS.items():
        st.session_state.setdefault(k, default)

    # Resolve the user profile: persisted preference > KB-having user >
    # first alphabetical. Done after setdefault so it only fires when
    # selected_user is still None (first render of a session).
    if st.session_state.selected_user is None:
        st.session_state.selected_user = _resolve_default_user()

    # Default image style resolves lazily the first time we need it — avoids
    # loading the YAML at import time when it's not used.
    if st.session_state.image_style is None:
        try:
            st.session_state.image_style = images_mod.default_style()
        except Exception:
            st.session_state.image_style = "kk"


def remember_user(user: str) -> None:
    """Persist the chosen user profile so the next session opens to it.
    Called by the sidebar profile selectbox when the user changes it."""
    prefs = _load_preferences()
    prefs["selected_user"] = user
    _save_preferences(prefs)


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
