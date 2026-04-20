"""Pipeline card — sac.steps stage indicator + st.status live log.

Renders only while a run is in flight or has just completed. The
``handle_submit()`` function is the single entry point that both input
paths (Transcribe-only, Full-pipeline) funnel through.
"""

from __future__ import annotations

from typing import Optional

import streamlit as st
import streamlit_antd_components as sac

from whisperforge_core import adapters as adapters_mod
from whisperforge_core import prompts as prompts_mod

from . import session

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

    with st.status("Running pipeline…", expanded=True) as status:
        try:
            # ---- Stage 0: Transcribe ------------------------------------
            if pending.source == "paste":
                # Already text — no transcription step.
                s.transcription = pending.payload
                s.transcription_segments = []
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
                status.write(f"✓ Transcript: {len(details.text):,} chars.")
                s.pipeline_stage_idx = 1

            # Stop here if user only wanted the transcript.
            if mode == "transcribe_only":
                status.update(label="Transcription complete.",
                              state="complete", expanded=False)
                s.pipeline_running = False
                s.pipeline_stage_idx = len(_STAGES) - 1
                return

            # ---- Full pipeline ---------------------------------------
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

            length_map = {"Brief": 500, "Standard": 1500, "Long-form": 3000}
            article_words = length_map.get(s.article_length, 1500)
            result = adapters.processor.run_pipeline(
                s.transcription,
                s.ai_provider, s.ai_model,
                knowledge_base=kb,
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
            s.pipeline_stage_idx = len(_STAGES) - 1

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
            status.update(label=f"Pipeline error: {e}", state="error")
            st.toast(f"Pipeline failed: {e}", icon=":material/error:")
        finally:
            s.pipeline_running = False
