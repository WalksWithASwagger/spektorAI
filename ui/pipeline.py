"""Pipeline card — sac.steps stage indicator + st.status live log.

Renders only while a run is in flight or has just completed. The
``handle_submit()`` function is the single entry point that both input
paths (Transcribe-only, Full-pipeline) funnel through.
"""

from __future__ import annotations

import time
from typing import Optional

import streamlit as st
import streamlit_antd_components as sac

from whisperforge_core import adapters as adapters_mod
from whisperforge_core import captures as captures_mod
from whisperforge_core import prompts as prompts_mod
from whisperforge_core import recipes as recipes_mod
from whisperforge_core import run_artifacts
from whisperforge_core import scorecards as scorecards_mod
from whisperforge_core.logging import get_logger

from . import session

logger = get_logger(__name__)

# Ordered stages for the sac.steps indicator. Kept short so they fit on one
# row in the default sidebar-plus-main layout.
_STAGES = [
    "Transcribe", "Clean", "Chapters", "Wisdom",
    "Outline", "Social", "Images", "Article", "Save",
]


def render() -> None:
    """Called unconditionally; only paints when a run is active or just
    finished. After a fresh clear_run, this becomes a no-op."""
    if not st.session_state.get("pipeline_running") and not st.session_state.get("transcription"):
        return

    st.markdown(
        "<div class='section-header'>Pipeline</div>", unsafe_allow_html=True,
    )
    with st.container(border=True):
        stage_idx = min(st.session_state.get("pipeline_stage_idx", 0),
                        len(_STAGES) - 1)
        sac.steps(
            items=[sac.StepsItem(title=s) for s in _STAGES],
            index=stage_idx,
            format_func="title",
            placement="horizontal",
            size="xs",
            return_index=True,
            key="pipeline_steps",
        )

        # If the run is marked running, execute it now inside st.status.
        if st.session_state.get("pipeline_running"):
            _execute_run()


def _execute_run() -> None:
    """The actual pipeline execution, wrapped in st.status so progress
    streams as collapsible log lines. This is the sole caller of the
    transcription + pipeline adapters in the UI layer."""
    pending = st.session_state.get("pending_input")
    if pending is None:
        st.session_state.pipeline_running = False
        return

    mode = st.session_state.get("_submit_mode", "full_pipeline")
    s = st.session_state
    adapters = adapters_mod.get_adapters()
    kb = prompts_mod.load_knowledge_base(s.selected_user) if s.selected_user else {}

    # Capture a start timestamp so the Run metrics block can report
    # wall-clock duration. End timestamp is written in `finally`.
    s.pipeline_started_at = time.time()
    s.pipeline_ended_at = None
    if not s.get("run_id"):
        s.run_id = run_artifacts.new_run_id()
    capture_record = _ensure_capture(pending, s.run_id)
    if capture_record:
        s.capture_id = capture_record.capture_id
    try:
        artifact_dir = run_artifacts.start_run(
            s.run_id, _run_metadata(pending, mode, s),
        )
        s.run_artifact_dir = str(artifact_dir)
    except Exception as e:
        logger.warning("failed to start run artifacts: %s", e)

    with st.status("Running pipeline…", expanded=True) as status:
        try:
            # ---- Stage 0: Transcribe ------------------------------------
            if pending.source in {"paste", "wispr_flow"}:
                # Already text — no transcription step.
                s.transcription = pending.payload
                s.transcription_segments = []
                _write_run_stage(s, "transcription", {
                    "source": pending.source,
                    "filename": pending.filename,
                    "text": s.transcription,
                    "segments": [],
                })
                status.write("📝 Using pasted text (no transcription needed).")
                s.pipeline_stage_idx = 1
            else:
                status.write(f"🎙 Transcribing `{pending.filename}`…")
                # Route through the active Transcriber adapter (direct or
                # HTTP depending on DEPLOY_MODE). transcribe_detailed
                # returns segments when the backend supports them.
                source = (pending.payload if pending.source == "record"
                          else pending.payload)
                suffix = (
                    "." + pending.filename.rsplit(".", 1)[-1]
                    if "." in pending.filename else ".mp3"
                )
                details = adapters.transcriber.transcribe_detailed(
                    source.getvalue(), suffix=suffix,
                )
                s.transcription = details.text
                s.transcription_segments = details.segments or []
                s.audio_file = pending.payload          # for Notion "Original Audio" bundle slot
                _write_run_stage(s, "transcription", {
                    "source": pending.source,
                    "filename": pending.filename,
                    "text": details.text,
                    "segments": details.segments or [],
                    "language": details.language,
                })
                status.write(f"✓ Transcript: {len(details.text):,} chars.")
                s.pipeline_stage_idx = 1

            # Stop here if user only wanted the transcript.
            if mode == "transcribe_only":
                status.update(label="Transcription complete.",
                              state="complete", expanded=False)
                s.pipeline_running = False
                s.pipeline_stage_idx = len(_STAGES) - 1
                _mark_run_status(s, "completed")
                _mark_capture_status(s, "completed")
                return

            # ---- Full pipeline ---------------------------------------
            _inspect_retrieval(s, status)
            # Progress callback writes to the sac.steps index and streams
            # a status line per stage.
            _stage_to_idx = {
                "Cleaning transcript...": 1,
                "Chaptering...": 2,
                "Extracting wisdom...": 3,
                "Creating outline...": 4,
                "Generating social media...": 5,
                "Creating image prompts...": 6,
                "Writing full article...": 7,
                "Critiquing draft...": 7,
                "Revising...": 7,
                "Generating images...": 6,
                "Fact-checking...": 7,
                "Done": 8,
            }

            last_label = {"value": ""}

            def progress_cb(frac: float, label: str) -> None:
                # Update the sac.steps indicator when we cross a stage
                # boundary; write a log line in st.status when the label
                # changes.
                if label != last_label["value"]:
                    status.write(f"  · {label}")
                    last_label["value"] = label
                    s.pipeline_stage_idx = _stage_to_idx.get(label, s.pipeline_stage_idx)

            def checkpoint_cb(stage: str, payload: dict) -> None:
                _write_run_stage(s, stage, payload)

            length_map = {"Brief": 500, "Standard": 1500, "Long-form": 3000}
            article_words = length_map.get(s.article_length, 1500)
            result = adapters.processor.run_pipeline(
                s.transcription,
                s.ai_provider, s.ai_model,
                knowledge_base=kb,
                cleanup=bool(s.cleanup_enabled),
                chapters=bool(s.chapters_enabled),
                segments=s.transcription_segments or None,
                progress=progress_cb,
                agentic=bool(s.agentic_drafting),
                fact_check=bool(s.fact_check_enabled),
                generate_images=bool(s.images_enabled),
                image_style=s.image_style,
                image_aspect_ratio=s.image_aspect,
                image_model=s.image_model,
                article_length_words=article_words,
                user=s.selected_user,
                rag_mode=s.get("rag_mode", "auto"),
                compare_provider=s.get("compare_provider"),
                compare_model=s.get("compare_model"),
                personas=s.get("selected_personas") or None,
                checkpoint=checkpoint_cb,
            )

            s.wisdom = result.wisdom or ""
            s.outline = result.outline or ""
            s.social_content = result.social_posts or ""
            s.image_prompts = result.image_prompts or ""
            s.article = result.article or ""
            s.chapters = result.chapters or []
            s.cleaned_transcript = result.cleaned_transcript
            s.article_critique = result.article_critique
            s.fact_check_flags = result.fact_check_flags or []
            s.fact_check_ran = bool(s.fact_check_enabled)
            s.generated_images = result.generated_images or []
            s.article_compare = result.article_compare
            s.compare_label = result.compare_label
            s.persona_articles = result.persona_articles or []
            s.scorecard_summary = _build_scorecard_summary(s)
            s.pipeline_stage_idx = len(_STAGES) - 1
            _write_run_stage(s, "scorecard", s.scorecard_summary)
            _write_run_stage(s, "session_output", {
                "wisdom": s.wisdom,
                "outline": s.outline,
                "social_content": s.social_content,
                "image_prompts": s.image_prompts,
                "article": s.article,
                "chapters": s.chapters,
                "fact_check_flags": s.fact_check_flags,
                "generated_images": s.generated_images,
                "article_compare": s.article_compare,
                "compare_label": s.compare_label,
                "persona_articles": s.persona_articles,
                "scorecard_summary": s.scorecard_summary,
            })
            _mark_run_status(s, "completed")
            _mark_capture_status(s, "completed")

            # Freeze the pipeline duration here — before the Notion
            # auto-save, so the Run metrics block doesn't double-count the
            # save roundtrip in the duration number.
            s.pipeline_ended_at = time.time()

            status.update(label="Pipeline complete — see Output below.",
                          state="complete", expanded=False)

            # Auto-save to Notion if enabled. Lazy import avoids the
            # ui.output ↔ ui.pipeline circular path at module load time.
            if s.get("auto_save_notion", True):
                from . import output as output_mod
                status.write("📤 Auto-saving to Notion…")
                url = output_mod._save_to_notion()
                if url:
                    s.last_notion_url = url
                    st.toast("Auto-saved to Notion!",
                             icon=":material/cloud_done:")
                else:
                    st.toast("Auto-save failed — check the Output card.",
                             icon=":material/error:")

        except Exception as e:
            _write_run_stage(s, "error", {
                "message": str(e),
                "stage_idx": s.get("pipeline_stage_idx", 0),
            })
            _mark_run_status(s, "failed", error=str(e))
            _mark_capture_status(s, "failed")
            status.update(label=f"Pipeline error: {e}", state="error")
            st.toast(f"Pipeline failed: {e}", icon=":material/error:")
        finally:
            # Stamp an end time if we didn't already (error path before
            # the explicit set above).
            if not s.pipeline_ended_at:
                s.pipeline_ended_at = time.time()
            s.pipeline_running = False


def _run_metadata(pending, mode: str, s) -> dict:
    return {
        "mode": mode,
        "source": pending.source,
        "filename": pending.filename,
        "capture": captures_mod.run_metadata(s.get("capture_id")),
        "recipe": recipes_mod.run_metadata(
            s.get("active_recipe_id"),
            s.get("active_recipe"),
            s.get("recipe_effective_settings"),
        ),
        "selected_user": s.selected_user,
        "provider": s.ai_provider,
        "model": s.ai_model,
        "settings": {
            "cleanup": bool(s.cleanup_enabled),
            "chapters": bool(s.chapters_enabled),
            "agentic": bool(s.agentic_drafting),
            "fact_check": bool(s.fact_check_enabled),
            "images": bool(s.images_enabled),
            "rag_mode": s.get("rag_mode", "auto"),
            "compare_provider": s.get("compare_provider"),
            "compare_model": s.get("compare_model"),
            "personas": s.get("selected_personas") or [],
        },
    }


def _ensure_capture(pending, run_id: str):
    capture_id = getattr(pending, "capture_id", None)
    if capture_id:
        try:
            return captures_mod.attach_run(capture_id, run_id, status="running")
        except Exception as e:
            logger.warning("failed to attach run to capture %s: %s", capture_id, e)

    text = pending.payload if pending.source in {"paste", "wispr_flow"} else None
    try:
        record = captures_mod.create_capture(
            source=pending.source,
            filename=pending.filename,
            title=getattr(pending, "title", None),
            text=text,
            metadata={"created_by": "streamlit_input"},
        )
        pending.capture_id = record.capture_id
        return captures_mod.attach_run(record.capture_id, run_id, status="running")
    except Exception as e:
        logger.warning("failed to create capture record: %s", e)
        return None


def _inspect_retrieval(s, status) -> None:
    user = s.get("selected_user")
    transcript = s.get("transcription") or ""
    if not user or not transcript or s.get("rag_mode", "auto") == "never":
        s.retrieval_inspector = None
        return
    try:
        from whisperforge_core.rag import retriever

        engaged = retriever.should_engage(user, mode=s.get("rag_mode", "auto"))
        stages = {}
        for stage in retriever.STAGE_AUGMENTATIONS:
            stages[stage] = [
                hit.to_dict()
                for hit in retriever.inspect(user, query=transcript, stage=stage)
            ]
        payload = {
            "user": user,
            "rag_mode": s.get("rag_mode", "auto"),
            "engaged": engaged,
            "query_excerpt": transcript[:360],
            "stages": stages,
        }
        s.retrieval_inspector = payload
        _write_run_stage(s, "retrieval_inspector", payload)
        hit_count = sum(len(items) for items in stages.values())
        status.write(f"📚 Retrieval inspector captured {hit_count} KB hits.")
    except Exception as e:
        logger.warning("retrieval inspection failed: %s", e)


def _build_scorecard_summary(s) -> dict:
    transcript = s.get("cleaned_transcript") or s.get("transcription") or ""
    return scorecards_mod.build_summary(
        article=s.get("article") or "",
        transcript=transcript,
        wisdom=s.get("wisdom") or "",
        outline=s.get("outline") or "",
        social_content=s.get("social_content") or "",
        image_prompts=s.get("image_prompts") or "",
        chapters=s.get("chapters") or [],
        source_receipts=_scorecard_source_receipts(s, transcript),
        retrieval_inspector=s.get("retrieval_inspector"),
        fact_check_flags=s.get("fact_check_flags") or [],
        fact_check_ran=bool(s.get("fact_check_ran")),
        recipe=s.get("active_recipe") or {},
        recipe_effective_settings=s.get("recipe_effective_settings") or {},
    )


def _scorecard_source_receipts(s, transcript: str) -> list[dict]:
    receipts = []
    recipe_meta = s.get("recipe_effective_settings")
    if recipe_meta:
        receipts.append({
            "source": "Recipe",
            "name": recipe_meta.get("recipe_name"),
        })
    capture_meta = captures_mod.run_metadata(s.get("capture_id"))
    if capture_meta:
        receipts.append({
            "source": "Capture",
            "title": capture_meta.get("title"),
        })
    if transcript:
        receipts.append({
            "source": "Transcript",
            "excerpt": transcript[:240],
        })
    retrieval_inspector = s.get("retrieval_inspector")
    if retrieval_inspector:
        stages = retrieval_inspector.get("stages") or {}
        receipts.append({
            "source": "Knowledge retrieval",
            "hits": sum(len(hits) for hits in stages.values()),
        })
    return receipts


def _write_run_stage(s, stage: str, payload: dict) -> None:
    run_id = s.get("run_id")
    if not run_id:
        return
    try:
        path = run_artifacts.write_stage(run_id, stage, payload)
        s.run_artifact_dir = str(path.parent.parent)
    except Exception as e:
        logger.warning("failed to write run artifact stage %s: %s", stage, e)


def _mark_run_status(s, status: str, *, error: Optional[str] = None) -> None:
    run_id = s.get("run_id")
    if not run_id:
        return
    try:
        run_artifacts.mark_status(run_id, status, error=error)
    except Exception as e:
        logger.warning("failed to mark run artifact status %s: %s", status, e)


def _mark_capture_status(s, status: str) -> None:
    capture_id = s.get("capture_id")
    if not capture_id:
        return
    try:
        captures_mod.mark_status(capture_id, status)
    except Exception as e:
        logger.warning("failed to mark capture status %s: %s", status, e)
