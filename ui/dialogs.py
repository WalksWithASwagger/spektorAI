"""All @st.dialog modals live here.

Streamlit dialogs are decorator-based: calling the decorated function
opens the modal. Since we can only open one dialog at a time, each
function here is self-contained (loads its own data, renders its own
controls, writes its own side effects).

Kept separate from the sidebar so the sidebar stays compact and these
heavy trees don't re-run on every keystroke somewhere else in the app.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

import streamlit as st

from whisperforge_core import history as history_mod
from whisperforge_core import images as images_mod
from whisperforge_core import prompts as prompts_mod
from whisperforge_core.config import DEFAULT_PROMPTS


# -----------------------------------------------------------------------
# Generation Settings — the old inline expander. Moved to a popover-sized
# dialog so the sidebar doesn't collapse mid-tweak.
# -----------------------------------------------------------------------
@st.dialog("Generation settings", width="medium")
def generation_settings() -> None:
    s = st.session_state
    st.caption("What the pipeline should do on each run.")

    st.markdown("**Content pipeline**")
    s.cleanup_enabled = st.checkbox(
        "Clean transcript (strip fillers/false-starts)",
        value=s.cleanup_enabled, key="gs_cleanup",
    )
    s.chapters_enabled = st.checkbox(
        "Chapter segmentation",
        value=s.chapters_enabled, key="gs_chapters",
    )
    s.agentic_drafting = st.checkbox(
        "Agentic drafting (draft → critique → revise)",
        value=s.agentic_drafting, key="gs_agentic",
        help="~2× cost/time, big quality jump on long-form.",
    )
    s.fact_check_enabled = st.checkbox(
        "Fact-check article against transcript",
        value=s.fact_check_enabled, key="gs_factcheck",
    )

    st.markdown("**Article length**")
    s.article_length = st.segmented_control(
        "Length", options=["Brief", "Standard", "Long-form"],
        default=s.article_length, key="gs_length",
        label_visibility="collapsed",
        help="Brief ≈ 500 words · Standard ≈ 1500 · Long-form ≈ 3000. "
             "Applied to the article + revise stages.",
    ) or s.article_length

    st.divider()
    st.markdown("**Output**")
    s.auto_save_notion = st.checkbox(
        "Auto-save to Notion when pipeline finishes",
        value=s.auto_save_notion, key="gs_autosave",
        help="Save the run automatically once the article stage completes. "
             "Disable if you want to review before publishing.",
    )
    s.auto_export_markdown = st.checkbox(
        "Also export a markdown copy (.cache/exports/)",
        value=s.auto_export_markdown, key="gs_mdexport",
        help="Obsidian-compatible .md with YAML frontmatter. Written "
             "alongside Notion save — great for local vaults.",
    )

    st.markdown("**Knowledge base retrieval**")
    s.rag_mode = st.segmented_control(
        "KB mode",
        options=["Auto", "Always", "Never"],
        default=s.rag_mode.capitalize() if isinstance(s.rag_mode, str) else "Auto",
        key="gs_rag_mode",
        label_visibility="collapsed",
        help=(
            "Auto = use RAG when your KB has >25 chunks (otherwise dump "
            "the whole KB since prompt-caching already wins on small KBs). "
            "Always = top-K retrieval every call. Never = legacy dump-"
            "everything mode."
        ),
    ) or "Auto"
    # Normalize UI-friendly label back to the internal lowercase key used
    # by rag.should_engage().
    s.rag_mode = s.rag_mode.lower()

    st.divider()
    st.markdown("**A/B provider compare** (optional)")
    st.caption(
        "When enabled, the article stage runs once more with an alternate "
        "model after the main run. Both articles land in the Output. "
        "Useful for deciding whether to promote a Haiku draft to Sonnet."
    )
    from whisperforge_core.config import LLM_MODELS
    _compare_options: list[str] = ["(off)"]
    for prov, mods in LLM_MODELS.items():
        for mid in mods.values():
            _compare_options.append(f"{prov}::{mid}")
    # Current setting → display label
    current_compare = "(off)"
    if s.compare_provider and s.compare_model:
        current_compare = f"{s.compare_provider}::{s.compare_model}"
    if current_compare not in _compare_options:
        current_compare = "(off)"
    chosen = st.selectbox(
        "Comparison model", _compare_options,
        index=_compare_options.index(current_compare),
        key="gs_compare",
        format_func=lambda v: v if v == "(off)" else v.replace("::", " · "),
    )
    if chosen == "(off)":
        s.compare_provider = None
        s.compare_model = None
    else:
        p, m = chosen.split("::", 1)
        s.compare_provider = p
        s.compare_model = m

    st.divider()
    st.markdown("**Personas** (optional)")
    st.caption(
        "Pick any combination. For each selected persona the article stage "
        "runs once more with a voice-specific directive. Each variant lands "
        "in its own tab in the Output + toggle in Notion. Costs and runtime "
        "scale linearly with the number of personas."
    )
    from whisperforge_core.config import BUILTIN_PERSONA_NAMES
    s.selected_personas = st.multiselect(
        "Generate persona variants",
        options=BUILTIN_PERSONA_NAMES,
        default=s.selected_personas or [],
        key="gs_personas",
        label_visibility="collapsed",
    )

    st.divider()
    st.markdown("**Image generation** (Nano Banana / Gemini)")
    s.images_enabled = st.checkbox(
        "Generate images from image_prompts",
        value=s.images_enabled, key="gs_images",
        help="~$0.039 per image on flash-image. Needs GOOGLE_API_KEY.",
    )
    style_opts = list(images_mod.list_styles().keys()) + ["none"]
    default_style = s.image_style or images_mod.default_style()
    s.image_style = st.selectbox(
        "Style", options=style_opts,
        index=style_opts.index(default_style) if default_style in style_opts else 0,
        key="gs_style",
    )
    s.image_aspect = st.selectbox(
        "Aspect ratio", options=["16:9", "1:1", "9:16"],
        index=["16:9", "1:1", "9:16"].index(s.image_aspect),
        key="gs_aspect",
    )
    s.image_model = st.selectbox(
        "Image model",
        options=["gemini-2.5-flash-image", "gemini-3-pro-image-preview"],
        index=["gemini-2.5-flash-image", "gemini-3-pro-image-preview"].index(s.image_model),
        key="gs_imgmodel",
    )

    if st.button("Done", type="primary", use_container_width=True):
        st.toast("Settings saved.", icon=":material/check:")
        st.rerun()


# -----------------------------------------------------------------------
# Prompts — single selectbox + text_area (replaces 5 stacked editors).
# -----------------------------------------------------------------------
_PROMPT_TYPES = [
    "transcript_cleanup", "chapters", "wisdom_extraction",
    "outline_creation", "social_media", "image_prompts",
    "article_writing", "article_critique", "article_revise",
]


@st.dialog("Prompt editor", width="large")
def prompts_editor() -> None:
    user = st.session_state.get("selected_user")
    if not user:
        st.info("Pick a user profile in the sidebar first.")
        return

    # Build the set of types this user has either as on-disk .md or as
    # custom_prompts/*.txt overrides.
    user_prompts = prompts_mod.load_user_prompts(user)
    available = sorted(set(_PROMPT_TYPES) | set(user_prompts.keys()))

    ptype = st.selectbox("Prompt type", available, key="pe_type")
    current = user_prompts.get(ptype) or DEFAULT_PROMPTS.get(ptype, "")
    is_custom = ptype in user_prompts

    st.caption(
        ("**Custom override active** — stored at "
         f"`prompts/{user}/custom_prompts/{ptype}.txt`.")
        if is_custom else
        f"Using the default prompt. Edit + save to create a per-user override."
    )

    new_text = st.text_area("Prompt template", value=current, height=300,
                            key=f"pe_text_{ptype}")

    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        if st.button("Save override", type="primary", use_container_width=True):
            if prompts_mod.save_custom_prompt(user, ptype, new_text):
                st.toast("Prompt saved.", icon=":material/check_circle:")
                st.rerun()
            else:
                st.error("Save failed — see logs.")
    with c2:
        if is_custom and st.button("Reset to default", use_container_width=True):
            # "Reset" means delete the custom override file.
            target = (prompts_mod.PROMPTS_DIR / user / "custom_prompts"
                      / f"{ptype}.txt")
            try:
                target.unlink()
                st.toast("Reset to default.", icon=":material/restart_alt:")
                st.rerun()
            except OSError as e:
                st.error(f"Couldn't remove override: {e}")
    with c3:
        if st.button("Close", use_container_width=True):
            st.rerun()


# -----------------------------------------------------------------------
# Knowledge Base — unified upload / view (was split into two stacked
# sections in the old layout).
# -----------------------------------------------------------------------
@st.dialog("Knowledge base", width="large")
def knowledge_base_manager() -> None:
    user = st.session_state.get("selected_user")
    if not user:
        st.info("Pick a user profile in the sidebar first.")
        return

    kb = prompts_mod.load_knowledge_base(user)
    st.caption(
        f"Files under `prompts/{user}/knowledge_base/` are prepended to every "
        "LLM system prompt so the model writes in your voice."
    )

    st.markdown("**Existing files**")
    if not kb:
        st.info("No knowledge base files yet. Upload one below.")
    else:
        selected = st.selectbox("View file", options=list(kb.keys()),
                                key="kb_view_pick")
        if selected:
            st.text_area("Content", value=kb[selected], height=220,
                         key=f"kb_view_{selected}", disabled=True)

    st.divider()
    st.markdown("**Add / replace file**")
    uploaded = st.file_uploader("Upload .md or .txt",
                                type=["md", "txt"],
                                key="kb_upload")
    if uploaded:
        stem = Path(uploaded.name).stem
        name = st.text_input("Filename (without extension)", value=stem,
                             key="kb_filename")
        if st.button("Save to knowledge base", type="primary",
                     use_container_width=True):
            target_dir = prompts_mod.PROMPTS_DIR / user / "knowledge_base"
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / f"{name}.md"
            try:
                target.write_bytes(uploaded.getvalue())
                st.toast(f"Saved {target.name}", icon=":material/check_circle:")
                st.rerun()
            except OSError as e:
                st.error(f"Save failed: {e}")


# -----------------------------------------------------------------------
# KB benchmark — measure legacy vs RAG injection size for a sample query.
# Pure measurement (no LLM calls) so running it is free and deterministic.
# -----------------------------------------------------------------------
@st.dialog("Benchmark KB modes", width="large")
def kb_benchmark() -> None:
    from whisperforge_core.rag import benchmark as bench_mod
    from whisperforge_core.rag.retriever import STAGE_AUGMENTATIONS

    s = st.session_state
    user = s.get("selected_user")
    if not user:
        st.info("Pick a user profile in the sidebar first.")
        return

    st.caption(
        "Measures how many input tokens each pipeline stage injects from "
        "your knowledge base under legacy (dump everything) vs RAG (top-K "
        "retrieval). No LLM calls — this is pure sizing + input-rate math, "
        "so running it is free."
    )

    # Query defaults to the current transcript/article excerpt when available,
    # otherwise a reasonable stub so Kris can still eyeball his KB without
    # first running a pipeline.
    default_query = (
        (s.get("transcription") or s.get("article") or "")[:2000]
        or "A talk about AI, creativity, and helping leaders adapt."
    )
    query = st.text_area(
        "Sample query (the 'user content' each stage will see)",
        value=default_query, height=120, key="bench_query",
    )

    col1, col2 = st.columns(2)
    with col1:
        stage = st.selectbox(
            "Stage", options=list(STAGE_AUGMENTATIONS.keys()),
            index=list(STAGE_AUGMENTATIONS.keys()).index("wisdom_extraction"),
            key="bench_stage",
        )
    with col2:
        scope = st.selectbox(
            "Scope", options=["Single stage", "All stages"],
            key="bench_scope",
        )

    provider = s.get("ai_provider") or "Anthropic"
    model = s.get("ai_model") or "claude-haiku-4-5"
    st.caption(f"Input-rate math uses the currently selected **{provider} {model}**.")

    if st.button("Run benchmark", type="primary", use_container_width=True,
                 key="bench_run"):
        with st.spinner("Measuring…"):
            try:
                if scope == "Single stage":
                    results = [bench_mod.compare_kb_modes(
                        user, query=query, stage=stage,
                        provider=provider, model=model,
                    )]
                else:
                    results = bench_mod.benchmark_all_stages(
                        user, query=query, provider=provider, model=model,
                    )
            except Exception as e:
                st.error(f"Benchmark failed: {e}")
                return

        rows = []
        for r in results:
            rows.append({
                "Stage": r["stage"],
                "Legacy tokens": r["legacy"]["tokens"],
                "RAG tokens": r["rag"]["tokens"],
                "Savings": f"{r['delta']['token_savings_pct']:.1f}%",
                "Legacy $": f"${r['legacy']['cost_usd']:.5f}",
                "RAG $": f"${r['rag']['cost_usd']:.5f}",
                "RAG chunks": r["rag"]["chunks"],
                "Anchor": r["rag"]["anchor"] or "—",
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

        # Summary when running all stages.
        if len(results) > 1:
            tot_legacy = sum(r["legacy"]["cost_usd"] for r in results)
            tot_rag = sum(r["rag"]["cost_usd"] for r in results)
            saved = tot_legacy - tot_rag
            pct = (saved / tot_legacy * 100) if tot_legacy else 0
            st.success(
                f"**Total per-run input cost:** legacy ${tot_legacy:.5f} → "
                f"RAG ${tot_rag:.5f} — saves **${saved:.5f} ({pct:.1f}%)** "
                f"before prompt caching. With Anthropic cache on the stable "
                f"legacy block, the real-world gap narrows ~10×."
            )


# -----------------------------------------------------------------------
# Run history — data_editor with clickable Notion links, sortable.
# -----------------------------------------------------------------------
@st.dialog("Recent runs", width="large")
def run_history() -> None:
    records = history_mod.recent(limit=50)
    if not records:
        st.info("No runs yet. Process an audio file or paste some text.")
        return

    rows = [
        {
            "When": r.timestamp.replace("T", " ").replace("Z", ""),
            "Title": r.title[:80],
            "Model": r.model,
            "Cost": r.cost_usd or 0.0,
            "Saved": r.cache_savings_usd or 0.0,
            "Notion": r.notion_url or "",
            "Agentic": bool((r.flags or {}).get("agentic")),
            "Fact-check": bool((r.flags or {}).get("fact_check")),
        }
        for r in records
    ]
    st.data_editor(
        rows,
        column_config={
            "Cost": st.column_config.NumberColumn("Cost $", format="$%.4f"),
            "Saved": st.column_config.NumberColumn("Saved $", format="$%.4f"),
            "Notion": st.column_config.LinkColumn(
                "Notion", display_text="Open",
            ),
            "Agentic": st.column_config.CheckboxColumn("Agentic"),
            "Fact-check": st.column_config.CheckboxColumn("Fact-check"),
        },
        disabled=True, hide_index=True, use_container_width=True,
        key="history_editor",
    )
    if st.button("Close", use_container_width=True):
        st.rerun()


# -----------------------------------------------------------------------
# Clear-run confirmation. Only triggered from the bottom-bar button.
# -----------------------------------------------------------------------
@st.dialog("Clear current run?")
def confirm_clear_run() -> None:
    st.warning(
        "This wipes the current transcription, generated content, and "
        "image results. Your settings (provider, model, toggles) are "
        "preserved. History stays on disk."
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Yes, clear", type="primary", use_container_width=True):
            from .session import clear_run
            clear_run()
            st.toast("Run cleared.", icon=":material/restart_alt:")
            st.rerun()
    with c2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()
