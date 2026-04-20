"""Sidebar — compact essentials only.

The audit found 18 sidebar widgets; most of them belonged elsewhere. This
keeps five visible surfaces (profile, provider, model, ⚙ More popover,
action buttons) and punts the heavy trees (Prompts, KB, History) into
on-demand dialogs.
"""

from __future__ import annotations

import streamlit as st

from whisperforge_core import images as images_mod
from whisperforge_core import prompts as prompts_mod
from whisperforge_core.config import LLM_MODELS
from whisperforge_core.llm import discover_ollama_models

from . import dialogs, session


def _providers_and_models() -> dict[str, dict[str, str]]:
    """Return the live LLM_MODELS dict with Ollama models refreshed from the
    running daemon (if any). Cached in session_state for one render."""
    cache_key = "_provider_model_cache"
    if cache_key in st.session_state:
        return st.session_state[cache_key]
    models = {**LLM_MODELS}
    try:
        ollama = discover_ollama_models()
        if ollama:
            models["Ollama (local)"] = ollama
    except Exception:
        pass  # Ollama not running = no discovery; fall back to static entry
    st.session_state[cache_key] = models
    return models


def render() -> None:
    """Render the entire sidebar."""
    with st.sidebar:
        # --- Profile -----------------------------------------------------
        st.markdown('<div class="section-header">Profile</div>',
                    unsafe_allow_html=True)
        users = prompts_mod.list_users()
        current_user = st.session_state.get("selected_user") or users[0]
        idx = users.index(current_user) if current_user in users else 0
        chosen_user = st.selectbox(
            "User", options=users, index=idx, key="sb_profile",
            label_visibility="collapsed",
        )
        # Persist whenever the user changes — next session opens to this one.
        if chosen_user != st.session_state.selected_user:
            session.remember_user(chosen_user)
        st.session_state.selected_user = chosen_user

        # --- Provider (segmented_control) -------------------------------
        st.markdown('<div class="section-header">Provider</div>',
                    unsafe_allow_html=True)
        models = _providers_and_models()
        provider_opts = list(models.keys())
        current_provider = st.session_state.get("ai_provider", "Anthropic")
        if current_provider not in provider_opts:
            current_provider = provider_opts[0]
        provider = st.segmented_control(
            "Provider",
            options=provider_opts,
            default=current_provider,
            key="sb_provider",
            label_visibility="collapsed",
        ) or current_provider
        # Remember the previously-selected model for this provider, if any.
        if provider != st.session_state.get("ai_provider"):
            # Switched providers — recall last model for the new one.
            st.session_state.ai_provider = provider
            first_model = list(models[provider].values())[0]
            st.session_state.ai_model = session.recall_model_for_provider(
                provider, fallback=first_model,
            )

        # --- Model -------------------------------------------------------
        model_map = models[provider]                 # {display_name: model_id}
        model_ids = list(model_map.values())
        current_model = st.session_state.get("ai_model")
        if current_model not in model_ids:
            current_model = model_ids[0]
        # Build the display list but use the ID as the stored value.
        labels_by_id = {v: k for k, v in model_map.items()}
        chosen = st.selectbox(
            "Model",
            options=model_ids,
            index=model_ids.index(current_model),
            format_func=lambda mid: labels_by_id.get(mid, mid),
            key="sb_model",
            label_visibility="collapsed",
        )
        st.session_state.ai_model = chosen
        session.remember_model_for_provider(provider, chosen)

        # --- Action buttons (open dialogs) ------------------------------
        st.markdown('<div class="section-header">Actions</div>',
                    unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✎ Prompts", use_container_width=True, key="btn_prompts"):
                dialogs.prompts_editor()
            if st.button("📚 KB", use_container_width=True, key="btn_kb"):
                dialogs.knowledge_base_manager()
            if st.button("📊 Benchmark", use_container_width=True, key="btn_bench"):
                dialogs.kb_benchmark()
        with c2:
            if st.button("📜 Runs", use_container_width=True, key="btn_runs"):
                dialogs.run_history()
            if st.button("⚙ More", use_container_width=True, key="btn_more"):
                dialogs.generation_settings()

        # --- Status footer ----------------------------------------------
        # Three tiny status dots — intentionally kept because they're part
        # of the aesthetic the user specifically called out.
        st.markdown(
            """
            <div class="sidebar-status">
                <span class="status-dot status-secure"></span> Encrypted ·
                <span class="status-dot status-sovereignty"></span> Sovereign ·
                <span class="status-dot status-offline"></span> Local-capable
            </div>
            """,
            unsafe_allow_html=True,
        )
