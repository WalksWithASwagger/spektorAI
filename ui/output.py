"""Output card — bordered containers per section, one Notion save path.

Replaces three different Save-to-Notion code paths that lived in the old
app.py (one auto-saved in Record tab, one explicit in Audio tab, one
inline in Text tab). There's now exactly one ``save_to_notion()`` that
everything funnels through.
"""

from __future__ import annotations

import hashlib
import os
from typing import Optional

import streamlit as st

from whisperforge_core import adapters as adapters_mod
from whisperforge_core import composition_review as review_mod
from whisperforge_core import cost as cost_mod
from whisperforge_core import export as export_mod
from whisperforge_core import history as history_mod
from whisperforge_core import llm, notion
from whisperforge_core import run_artifacts
from whisperforge_core import captures as captures_mod
from whisperforge_core import scorecards as scorecards_mod

from . import review as review_ui
from . import session


def render() -> None:
    """Render the output card if anything's available. No-op on fresh sessions."""
    if not session.has_output():
        return

    st.markdown(
        "<div class='section-header'>Output</div>", unsafe_allow_html=True,
    )
    s = st.session_state

    # Collapsed section tabs keep the page short. Order matches the
    # Notion page layout so screenshots line up.
    _has_compare = bool(s.get("article_compare"))
    _personas = s.get("persona_articles") or []
    tab_labels = ["📝 Article", "🧭 Review"]
    if _has_compare:
        tab_labels.append("⚖ Compare")
    # One tab per persona variant — truncated name to keep tabs single-line.
    for pa in _personas:
        name = (pa.get("name") or "Persona").strip()
        tab_labels.append(f"🎭 {name[:18]}")
    tab_labels += ["🎯 Wisdom", "🗺 Outline", "📣 Social",
                   "🎨 Image prompts", "📑 Chapters", "🖼 Images"]
    tabs = st.tabs(tab_labels)

    idx = 0
    with tabs[idx]:
        _section("Article", s.article, key="article")
    idx += 1
    with tabs[idx]:
        review_ui.render()
    idx += 1
    if _has_compare:
        with tabs[idx]:
            _section(
                f"Article · {s.get('compare_label', 'alternate')}",
                s.article_compare, key="article_compare",
            )
            st.caption(
                "Alternate-provider article from the same transcript. "
                "Use the thumbs to mark which voice landed."
            )
        idx += 1
    for i, pa in enumerate(_personas):
        with tabs[idx]:
            _section(
                f"Persona · {pa.get('name', 'Persona')}",
                pa.get("text") or "",
                key=f"persona_{i}",
            )
        idx += 1
    with tabs[idx]:
        _section("Wisdom", s.wisdom, key="wisdom")
    idx += 1
    with tabs[idx]:
        _section("Outline", s.outline, key="outline")
    idx += 1
    with tabs[idx]:
        _section("Social", s.social_content, key="social")
    idx += 1
    with tabs[idx]:
        _section("Image prompts", s.image_prompts, key="image_prompts")
    idx += 1
    with tabs[idx]:
        _chapters_panel()
    idx += 1
    with tabs[idx]:
        _images_panel()

    # Unified Save to Notion footer.
    st.divider()
    _notion_save_bar()


def _section(label: str, content: str, *, key: str) -> None:
    """Bordered container + content + thumbs feedback."""
    if not content:
        st.info(f"No {label.lower()} generated yet.")
        return
    with st.container(border=True):
        st.markdown(content)
        # st.feedback returns 0 (thumbs down) or 1 (thumbs up) when picked.
        # We persist it in session_state so re-renders keep the selection.
        st.feedback("thumbs", key=f"fb_{key}")


def _chapters_panel() -> None:
    chapters = st.session_state.chapters
    if not chapters:
        st.info("No chapters for this run.")
        return
    with st.container(border=True):
        for c in chapters:
            ts = c.get("start_seconds")
            ts_prefix = ""
            if isinstance(ts, (int, float)):
                total = int(ts)
                h, rem = divmod(total, 3600)
                m, sec = divmod(rem, 60)
                ts_prefix = (f"**[{h}:{m:02d}:{sec:02d}]** "
                             if h else f"**[{m}:{sec:02d}]** ")
            st.markdown(f"- {ts_prefix}**{c.get('title', '')}** — {c.get('summary', '')}")


def _images_panel() -> None:
    imgs = st.session_state.generated_images or []
    if not imgs:
        st.info("Image generation wasn't enabled for this run "
                "(toggle in ⚙ More → Generation Settings).")
        return
    succeeded = [g for g in imgs if g.get("succeeded")]
    failed = [g for g in imgs if not g.get("succeeded")]
    st.caption(f"{len(succeeded)} of {len(imgs)} images generated.")
    if succeeded:
        cols = st.columns(min(3, len(succeeded)))
        for i, img in enumerate(succeeded):
            with cols[i % len(cols)]:
                st.image(img["path"], use_container_width=True)
                st.caption(img["prompt"][:110] + ("…" if len(img["prompt"]) > 110 else ""))
                try:
                    with open(img["path"], "rb") as f:
                        st.download_button(
                            "Download", data=f.read(),
                            file_name=os.path.basename(img["path"]),
                            mime="image/png",
                            key=f"dl_{i}_{img['path']}",
                            use_container_width=True,
                        )
                except OSError:
                    pass
    for img in failed:
        st.warning(
            f"⚠️ {img.get('error', 'unknown error')[:200]}\n\n"
            f"**Prompt:** {img.get('prompt', '')[:200]}"
        )


def _notion_save_bar() -> None:
    s = st.session_state
    already = bool(s.last_notion_url)
    c1, c2, c3 = st.columns([3, 2, 2])
    with c1:
        if already:
            st.markdown(
                f"**Saved to Notion.** [Open the page]({s.last_notion_url})")
        else:
            st.caption("Publish this run, or download a local markdown copy.")
    with c2:
        if st.button("💾 Markdown", use_container_width=True, key="save_md"):
            path = _export_markdown()
            if path:
                st.toast(f"Saved: {path.name}",
                         icon=":material/description:")
                st.session_state._last_md_path = str(path)
                st.rerun()
    with c3:
        if st.button("📤 Save to Notion", type="primary",
                     use_container_width=True, key="save_notion_unified"):
            url = _save_to_notion()
            if url:
                s.last_notion_url = url
                st.toast("Saved to Notion!", icon=":material/check_circle:")
                st.rerun()

    # Surface download button for the most recent markdown export.
    last_md = st.session_state.get("_last_md_path")
    if last_md:
        try:
            with open(last_md, "rb") as f:
                st.download_button(
                    "⬇ Download markdown",
                    data=f.read(),
                    file_name=os.path.basename(last_md),
                    mime="text/markdown",
                    key="dl_md",
                )
        except OSError:
            pass


def _export_markdown() -> Optional["Path"]:
    """Build a ContentBundle from session_state and write it as markdown."""
    from pathlib import Path
    s = st.session_state
    bundle = _build_bundle()
    try:
        path = export_mod.export(bundle, notion_url=s.last_notion_url)
        _record_run_export("markdown", str(path))
        return path
    except Exception as e:
        st.error(f"Markdown export failed: {e}")
        return None


def _build_bundle() -> notion.ContentBundle:
    """Shared ContentBundle construction used by both the Notion save and
    markdown export paths — extracted so we don't drift between them."""
    s = st.session_state
    transcript = s.cleaned_transcript or s.transcription or ""
    audio_filename = None
    if getattr(s.audio_file, "name", None):
        audio_filename = s.audio_file.name

    try:
        title_suffix = llm.generate_title(transcript)
    except Exception:
        title_suffix = "Untitled"
    title = f"WHISPER: {title_suffix}"
    try:
        summary = llm.generate_summary(transcript)
    except Exception:
        summary = "Summary unavailable."
    try:
        tags = llm.generate_tags(
            (transcript or "") + " " + (s.wisdom or ""), max_tags=5,
        ) or ["whisperforge"]
    except Exception:
        tags = ["whisperforge"]

    models_used = []
    if s.ai_provider and s.ai_model:
        models_used.append(f"{s.ai_provider} {s.ai_model}")
    if transcript:
        models_used.append(
            f"{os.getenv('TRANSCRIPTION_BACKEND', 'openai')} transcribe"
        )

    source_receipts = []
    recipe_meta = s.get("recipe_effective_settings")
    active_recipe = s.get("active_recipe") or {}
    if recipe_meta:
        source_receipts.append({
            "source": "Recipe",
            "recipe_id": recipe_meta.get("recipe_id"),
            "name": recipe_meta.get("recipe_name"),
            "manifest_source": recipe_meta.get("source"),
            "stages": ", ".join(recipe_meta.get("stages") or []),
            "outputs": ", ".join(recipe_meta.get("output_sections") or []),
            "handoff_targets": ", ".join(recipe_meta.get("handoff_targets") or []),
        })
    capture_meta = captures_mod.run_metadata(s.get("capture_id"))
    if capture_meta:
        source_receipts.append({
            "source": "Capture",
            "capture_id": capture_meta.get("capture_id"),
            "capture_source": capture_meta.get("source"),
            "title": capture_meta.get("title"),
            "filename": capture_meta.get("filename"),
            "sha256": capture_meta.get("text_sha256"),
            "excerpt": capture_meta.get("text_excerpt"),
        })
    if transcript:
        receipt = {
            "source": "Transcript",
            "sha256": hashlib.sha256(transcript.encode("utf-8")).hexdigest(),
            "excerpt": transcript[:240],
        }
        if audio_filename:
            receipt["audio_filename"] = audio_filename
        source_receipts.append(receipt)
    retrieval_inspector = s.get("retrieval_inspector")
    if retrieval_inspector:
        stages = retrieval_inspector.get("stages") or {}
        anchors = sorted({
            hit.get("doc_name")
            for hits in stages.values()
            for hit in hits
            if hit.get("role") == "voice_anchor" and hit.get("doc_name")
        })
        source_receipts.append({
            "source": "Knowledge retrieval",
            "rag_mode": retrieval_inspector.get("rag_mode"),
            "engaged": retrieval_inspector.get("engaged"),
            "stages": len(stages),
            "hits": sum(len(hits) for hits in stages.values()),
            "voice_anchors": ", ".join(anchors) if anchors else "",
        })
    for note in (s.get("songforge") or {}).get("source_notes") or []:
        source_receipts.append({
            "source": "SongForge",
            "note_source": note.get("source"),
            "excerpt": note.get("excerpt"),
            "informs": note.get("informs"),
        })
    review_summary = review_mod.build_summary(
        source_receipts=source_receipts,
        retrieval_inspector=retrieval_inspector,
        fact_check_flags=s.fact_check_flags or [],
        article_critique=s.article_critique,
        article_compare=s.get("article_compare"),
        persona_articles=s.get("persona_articles") or [],
        chapters=s.chapters or [],
    )
    source_receipts.append(review_mod.receipt_for_summary(review_summary))
    scorecard_summary = review_ui.scorecard_summary_from_state(
        s, source_receipts=source_receipts,
    )
    s.scorecard_summary = scorecard_summary
    source_receipts.append(scorecards_mod.receipt_for_summary(scorecard_summary))

    # Run metrics — folded into the bundle so the Notion page + markdown
    # export carry their own receipt instead of forcing a cross-ref against
    # history.json. Safe on partial runs: estimate_cost() returns zeroes
    # when the ledger is empty, duration is None when timestamps aren't set.
    b = cost_mod.estimate_cost()
    started = s.get("pipeline_started_at")
    ended = s.get("pipeline_ended_at")
    duration = (ended - started) if (started and ended) else None
    run_metrics = {
        "total_usd": round(b.total_usd, 6),
        "llm_usd": round(b.llm_usd, 6),
        "asr_usd": round(b.asr_usd, 6),
        "cache_savings_usd": round(b.cache_savings_usd, 6),
        "calls": b.calls,
        "input_tokens": b.input_tokens,
        "output_tokens": b.output_tokens,
        "cache_read_tokens": b.cache_read_tokens,
        "cache_write_tokens": b.cache_write_tokens,
        "duration_seconds": duration,
        "backend": os.getenv("TRANSCRIPTION_BACKEND", "openai"),
        "flags": {
            "agentic": bool(s.agentic_drafting),
            "fact_check": bool(s.fact_check_ran),
            "chapters": bool(s.chapters),
            "images": bool(s.generated_images),
            "rag": s.get("rag_mode", "auto") != "never",
            "compare": bool(s.get("article_compare")),
            "personas": bool(s.get("persona_articles")),
            "songforge": bool(s.get("songforge")),
        },
        "capture": capture_meta,
        "recipe": {
            "id": s.get("active_recipe_id"),
            "manifest": active_recipe,
            "effective_settings": recipe_meta,
        } if recipe_meta else None,
        "retrieval_inspector": retrieval_inspector,
        "composition_review": review_summary,
        "scorecard": scorecard_summary,
    }

    return notion.ContentBundle(
        title=title,
        transcript=transcript,
        wisdom=s.wisdom or "",
        outline=s.outline or "",
        social_content=s.social_content or "",
        image_prompts=s.image_prompts or "",
        article=s.article or "",
        summary=summary,
        tags=tags,
        audio_filename=audio_filename,
        models_used=models_used,
        chapters=s.chapters or [],
        article_compare=s.get("article_compare"),
        compare_label=s.get("compare_label"),
        persona_articles=s.get("persona_articles") or [],
        article_critique=s.article_critique,
        fact_check_flags=s.fact_check_flags or [],
        fact_check_ran=bool(s.fact_check_ran),
        run_metrics=run_metrics,
        source_receipts=source_receipts,
    )


def _save_to_notion() -> Optional[str]:
    """Save the current session_state bundle to Notion, record a history
    entry, and — if auto_export_markdown is enabled — also write a
    markdown copy to .cache/exports/."""
    s = st.session_state
    adapters = adapters_mod.get_adapters()
    bundle = _build_bundle()

    try:
        url = adapters.storage.save(bundle)
    except Exception as e:
        st.error(f"Notion save failed: {e}")
        return None
    if not url:
        st.error("Notion save returned no URL.")
        return None

    # Optional side-write of a markdown copy.
    if s.get("auto_export_markdown"):
        try:
            md_path = export_mod.export(bundle, notion_url=url)
            s._last_md_path = str(md_path)
            _record_run_export("markdown", str(md_path))
        except Exception as e:
            logger_warn = getattr(st, "toast", None)
            if logger_warn:
                st.toast(f"Markdown export skipped: {e}", icon=":material/warning:")
    _record_run_export("notion", url)

    # Append history so the Runs dialog shows this run next open.
    b = cost_mod.estimate_cost()
    history_mod.upsert(history_mod.RunRecord(
        timestamp=history_mod.now_iso(),
        title=bundle.title,
        run_id=s.get("run_id"),
        run_path=s.get("run_artifact_dir"),
        markdown_path=s.get("_last_md_path"),
        notion_url=url,
        audio_filename=bundle.audio_filename,
        provider=s.ai_provider or "",
        model=s.ai_model or "",
        duration_seconds=float((bundle.run_metrics or {}).get("duration_seconds") or 0.0),
        cost_usd=round(b.total_usd, 6),
        cache_savings_usd=round(b.cache_savings_usd, 6),
        flags={
            "agentic": bool(s.agentic_drafting),
            "fact_check": bool(s.fact_check_ran),
            "chapters": bool(s.chapters),
            "images": bool(s.generated_images),
            "backend": os.getenv("TRANSCRIPTION_BACKEND", "openai"),
        },
        scorecard=s.get("scorecard_summary") or (bundle.run_metrics or {}).get("scorecard") or {},
    ))
    return url


def _record_run_export(kind: str, value: str) -> None:
    run_id = st.session_state.get("run_id")
    if not run_id:
        return
    try:
        run_artifacts.record_export(run_id, kind, value)
        _refresh_scorecard_after_export(run_id)
    except Exception:
        pass


def _refresh_scorecard_after_export(run_id: str) -> None:
    manifest = run_artifacts.load_manifest(run_id)
    exports = manifest.get("exports") or []
    summary = review_ui.scorecard_summary_from_state(st.session_state, exports=exports)
    st.session_state.scorecard_summary = summary
    run_artifacts.write_stage(run_id, "scorecard", summary)

    session_output = run_artifacts.load_stage_payload(run_id, "session_output")
    if session_output:
        session_output["scorecard_summary"] = summary
        run_artifacts.write_stage(run_id, "session_output", session_output)
