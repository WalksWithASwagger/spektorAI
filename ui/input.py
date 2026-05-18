"""Input card — three tabs, one handler.

The old layout had three input tabs each with their own transcribe/process/
export code path (~400 LoC of near-duplicate logic at app.py:525-866).
This module collapses that into three tiny tab renderers that all produce
a ``PendingInput`` envelope, plus a single ``handle_submit()`` that does
the work regardless of source.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Optional

import streamlit as st

from whisperforge_core import captures as captures_mod

SourceType = Literal["upload", "record", "paste", "wispr_flow"]
SubmitMode = Literal["transcribe_only", "full_pipeline"]


@dataclass
class PendingInput:
    """What the user has queued up, regardless of which tab they used."""
    source: SourceType
    payload: Any           # UploadedFile for audio, str for text
    filename: str          # always set, matters for Notion's "Original Audio"
    capture_id: Optional[str] = None
    title: Optional[str] = None


def render() -> None:
    """Render the input card with three tabs. Writes to
    ``st.session_state.pending_input`` and surfaces two buttons
    (Transcribe / I'm Feeling Lucky). Returns nothing — the buttons set
    ``pipeline_running`` which the pipeline card picks up."""
    st.markdown(
        "<div class='section-header'>Input</div>", unsafe_allow_html=True,
    )

    with st.container(border=True):
        tabs = st.tabs(["📂 Upload", "🎙 Record", "✎ Paste"])

        with tabs[0]:
            up = st.file_uploader(
                "Upload audio",
                type=["mp3", "wav", "ogg", "m4a"],
                key="in_upload",
                label_visibility="collapsed",
                help="Up to 500 MB. Large files auto-chunk.",
            )
            if up is not None:
                st.audio(up, format="audio/wav")
                st.session_state.pending_input = PendingInput(
                    source="upload", payload=up, filename=up.name,
                )

        with tabs[1]:
            rec = st.audio_input(
                "Record a note", key="in_record",
                label_visibility="collapsed",
            )
            if rec is not None:
                st.audio(rec, format="audio/wav")
                ts = datetime.now().strftime("%Y%m%d-%H%M%S")
                # Preserve the filename-timestamp convention so Notion's
                # "Original Audio" field stays meaningful.
                rec.name = getattr(rec, "name", None) or f"recording-{ts}.wav"
                st.session_state.pending_input = PendingInput(
                    source="record", payload=rec, filename=rec.name,
                )

        with tabs[2]:
            source_label = st.segmented_control(
                "Text source",
                options=["Wispr Flow", "Notes"],
                default="Wispr Flow",
                key="in_paste_source",
                label_visibility="collapsed",
                help="Wispr Flow paste keeps the capture source explicit in run artifacts.",
            ) or "Wispr Flow"
            text = st.text_area(
                "Paste a transcript, Wispr Flow dictation, or any prose",
                height=180, key="in_paste",
                label_visibility="collapsed",
                placeholder="Drop in a Wispr Flow dictation, transcript, or some notes...",
            )
            if text and text.strip():
                source = "wispr_flow" if source_label == "Wispr Flow" else "paste"
                prefix = "wispr-flow" if source == "wispr_flow" else "text"
                existing = st.session_state.get("pending_input")
                existing_capture = (
                    getattr(existing, "capture_id", None)
                    if getattr(existing, "payload", None) == text else None
                )
                st.session_state.pending_input = PendingInput(
                    source=source, payload=text,
                    filename=f"{prefix}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt",
                    capture_id=existing_capture,
                    title=_title_from_text(text),
                )
                if st.button("Save to capture inbox", use_container_width=True,
                             key="save_text_capture"):
                    record = captures_mod.create_capture(
                        source=source,
                        filename=st.session_state.pending_input.filename,
                        title=st.session_state.pending_input.title,
                        text=text,
                    )
                    st.session_state.pending_input.capture_id = record.capture_id
                    st.session_state.capture_id = record.capture_id
                    st.toast("Saved to capture inbox.", icon=":material/inbox:")

        # Action buttons — disabled until input ready
        pending = st.session_state.get("pending_input")
        ready = pending is not None
        c1, c2 = st.columns(2)
        with c1:
            txn_clicked = st.button(
                "Transcribe only",
                disabled=not ready or pending.source in {"paste", "wispr_flow"},
                use_container_width=True,
                help="Just run ASR — useful for double-checking the transcript "
                     "before committing to a full pipeline run.",
                key="btn_transcribe_only",
            )
        with c2:
            lucky_clicked = st.button(
                "I'm Feeling Lucky",
                type="primary",
                disabled=not ready,
                use_container_width=True,
                help="Run the whole pipeline and save to Notion.",
                key="btn_feeling_lucky",
            )

        if not ready:
            st.caption("Drop a file, record, or paste to begin.")

    # Mode-setting side effect — actual pipeline work happens in
    # ui.pipeline.render() because that's where st.status lives.
    if txn_clicked and ready:
        st.session_state._submit_mode = "transcribe_only"
        st.session_state.pipeline_running = True
        st.rerun()
    elif lucky_clicked and ready:
        st.session_state._submit_mode = "full_pipeline"
        st.session_state.pipeline_running = True
        st.rerun()


def _title_from_text(text: str) -> str:
    line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    return (line[:80] if line else "Untitled text capture")
