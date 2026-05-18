"""All @st.dialog modals live here.

Streamlit dialogs are decorator-based: calling the decorated function
opens the modal. Since we can only open one dialog at a time, each
function here is self-contained (loads its own data, renders its own
controls, writes its own side effects).

Kept separate from the sidebar so the sidebar stays compact and these
heavy trees don't re-run on every keystroke somewhere else in the app.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import streamlit as st

from whisperforge_core import captures as captures_mod
from whisperforge_core import history as history_mod
from whisperforge_core import images as images_mod
from whisperforge_core import kb_audit as kb_audit_mod
from whisperforge_core import prompts as prompts_mod
from whisperforge_core import run_artifacts
from whisperforge_core.config import DEFAULT_PROMPTS
from .input import PendingInput


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
    persona_options = list(prompts_mod.list_personas(s.selected_user).keys())
    selected_personas = [
        name for name in (s.selected_personas or [])
        if name in persona_options
    ]
    s.selected_personas = st.multiselect(
        "Generate persona variants",
        options=persona_options,
        default=selected_personas,
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

    audit = kb_audit_mod.audit_profile(user)
    kb = prompts_mod.load_knowledge_base(user)
    st.caption(
        f"Files under `prompts/{user}/knowledge_base/` are prepended to every "
        "LLM system prompt so the model writes in your voice."
    )
    with st.expander("Profile OS summary", expanded=False):
        st.code(prompts_mod.profile_summary(user), language="text")
        profile_os = prompts_mod.load_profile_os(user)
        if profile_os["validation"]:
            for issue in profile_os["validation"][:8]:
                st.warning(issue["message"])
        else:
            st.success("Profile manifest references and defaults look valid.")

    summary = audit.to_dict()["summary"]
    st.markdown(
        f"**Health:** {summary['documents']} files · "
        f"{summary['approx_tokens']:,} est. tokens · "
        f"{summary['warnings']} signal(s)"
    )
    audit_json = json.dumps(audit.to_dict(), indent=2)
    st.download_button(
        "Download audit JSON",
        data=audit_json,
        file_name=f"{user}-knowledge-base-audit.json",
        mime="application/json",
        use_container_width=True,
    )
    with st.expander("Copy audit report"):
        st.code(audit_json, language="json")
    if audit.warnings:
        for warning in audit.warnings[:6]:
            message = warning.message
            if warning.severity == "warning":
                st.warning(message)
            else:
                st.info(message)
    if audit.documents:
        st.dataframe(
            [
                {
                    "File": Path(doc.path).name,
                    "Role": doc.role,
                    "Tokens": doc.approx_tokens,
                    "Modified": doc.modified_at[:10],
                }
                for doc in audit.documents
            ],
            use_container_width=True,
            hide_index=True,
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
# Capture inbox — durable Wispr Flow / note / audio intake records.
# -----------------------------------------------------------------------
@st.dialog("Capture inbox", width="large")
def capture_inbox() -> None:
    records = captures_mod.list_captures(limit=100)
    if not records:
        st.info("No captures yet. Paste Wispr Flow text or run audio once to seed the inbox.")
        return

    rows = [
        {
            "When": r.created_at.replace("T", " ").replace("Z", ""),
            "Source": r.source,
            "Title": r.title,
            "Status": r.status,
            "Runs": len(r.run_ids),
            "ID": r.capture_id,
        }
        for r in records
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)

    ids = [r.capture_id for r in records]
    selected = st.selectbox(
        "Load text capture",
        options=ids,
        format_func=lambda cid: next(
            (r.title for r in records if r.capture_id == cid),
            cid,
        ),
        key="capture_pick",
    )
    record = next((r for r in records if r.capture_id == selected), None)
    if record and record.input_path:
        text = captures_mod.read_capture_text(record.capture_id)
        st.text_area("Capture text", value=text, height=180, disabled=True)
        if st.button("Use as pending input", type="primary", use_container_width=True):
            st.session_state.pending_input = PendingInput(
                source="wispr_flow" if record.source == "wispr_flow" else "paste",
                payload=text,
                filename=record.filename or f"{record.capture_id}.txt",
                capture_id=record.capture_id,
                title=record.title,
            )
            st.session_state.capture_id = record.capture_id
            st.toast("Capture loaded into the input queue.", icon=":material/inbox:")
            st.rerun()
    elif record:
        st.caption("This capture has no text payload to load directly.")


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

    if st.button("Inspect retrieval", use_container_width=True,
                 key="bench_inspect"):
        from whisperforge_core.rag import retriever

        try:
            hits = retriever.inspect(user, query=query, stage=stage)
        except Exception as e:
            st.error(f"Retrieval inspection failed: {e}")
            return
        if not hits:
            st.info("No retrieval hits for this query.")
            return
        st.dataframe(
            [
                {
                    "Role": hit.role,
                    "Score": round(hit.score, 3),
                    "Source": hit.chunk.doc_name,
                    "Section": hit.chunk.section_path or "-",
                    "Tokens": hit.chunk.token_count,
                    "Excerpt": hit.chunk.text.strip()[:160],
                }
                for hit in hits
            ],
            use_container_width=True,
            hide_index=True,
        )


# -----------------------------------------------------------------------
# Run history — data_editor with clickable Notion links, sortable.
# -----------------------------------------------------------------------
@st.dialog("Recent runs", width="large")
def run_history() -> None:
    records = history_mod.recent(limit=50)
    manifests = run_artifacts.list_manifests(limit=50)
    if not records and not manifests:
        st.info("No runs yet. Process an audio file or paste some text.")
        return

    if manifests:
        st.markdown("**Run artifacts**")
        summaries = [run_artifacts.summarize_manifest(item) for item in manifests]
        st.data_editor(
            summaries,
            column_config={
                "partial": st.column_config.CheckboxColumn("Partial"),
                "error": st.column_config.TextColumn("Error"),
            },
            disabled=True, hide_index=True, use_container_width=True,
            key="run_artifact_editor",
        )
        choices = [item["run_id"] for item in summaries if item["run_id"]]
        selected = st.selectbox("Run to reopen", choices, key="run_reopen_select") if choices else None
        c1, c2 = st.columns(2)
        with c1:
            if selected and st.button("Reopen output", use_container_width=True, key="reopen_run"):
                ok = _reopen_run(selected)
                if ok:
                    st.toast("Run reopened. Close this dialog to review or retry exports.", icon=":material/open_in_new:")
                else:
                    st.warning("That run has no saved output stage yet. Partial metadata is visible above.")
        with c2:
            if selected:
                run_path = run_artifacts.run_dir(selected)
                st.link_button("Open artifact folder", run_path.resolve().as_uri(), use_container_width=True)

    if not records:
        return

    rows = [
        {
            "When": r.timestamp.replace("T", " ").replace("Z", ""),
            "Title": r.title[:80],
            "Model": r.model,
            "Cost": r.cost_usd or 0.0,
            "Saved": r.cache_savings_usd or 0.0,
            "Verdict": (r.scorecard or {}).get("verdict_label", ""),
            "Score": (r.scorecard or {}).get("average_score", None),
            "Notion": r.notion_url or "",
            "Artifacts": Path(r.run_path).resolve().as_uri() if r.run_path else "",
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
            "Score": st.column_config.NumberColumn("Score", format="%d"),
            "Notion": st.column_config.LinkColumn(
                "Notion", display_text="Open",
            ),
            "Artifacts": st.column_config.LinkColumn(
                "Artifacts", display_text="Open",
            ),
            "Agentic": st.column_config.CheckboxColumn("Agentic"),
            "Fact-check": st.column_config.CheckboxColumn("Fact-check"),
        },
        disabled=True, hide_index=True, use_container_width=True,
        key="history_editor",
    )
    if st.button("Close", use_container_width=True):
        st.rerun()


def _reopen_run(run_id: str) -> bool:
    output = run_artifacts.load_stage_payload(run_id, "session_output")
    if not output:
        return False
    transcription = run_artifacts.load_stage_payload(run_id, "transcription")
    retrieval = run_artifacts.load_stage_payload(run_id, "retrieval_inspector")
    scorecard = run_artifacts.load_stage_payload(run_id, "scorecard")
    s = st.session_state
    for key in (
        "wisdom", "outline", "social_content", "image_prompts", "article",
        "chapters", "fact_check_flags", "generated_images", "article_compare",
        "compare_label", "persona_articles", "scorecard_summary",
    ):
        if key in output:
            s[key] = output[key]
    s.transcription = transcription.get("text", s.get("transcription", ""))
    s.transcription_segments = transcription.get("segments", [])
    s.retrieval_inspector = retrieval or s.get("retrieval_inspector")
    if scorecard:
        s.scorecard_summary = scorecard
    s.run_id = run_id
    s.run_artifact_dir = str(run_artifacts.run_dir(run_id))
    s.pipeline_running = False
    s.pipeline_stage_idx = 8
    s.last_notion_url = _latest_export_url(run_id, "notion")
    return True


def _latest_export_url(run_id: str, kind: str) -> str | None:
    manifest = run_artifacts.load_manifest(run_id)
    exports = [item for item in manifest.get("exports", []) if item.get("kind") == kind]
    return (exports[-1] or {}).get("value") if exports else None


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
