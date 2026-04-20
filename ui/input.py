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

from whisperforge_core import adapters as adapters_mod

SourceType = Literal["upload", "record", "paste"]
SubmitMode = Literal["transcribe_only", "full_pipeline"]


@dataclass
class PendingInput:
    """What the user has queued up, regardless of which tab they used."""
    source: SourceType
    payload: Any           # UploadedFile for audio, str for text
    filename: str          # always set, matters for Notion's "Original Audio"


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
            text = st.text_area(
                "Paste a transcript or any prose",
                height=180, key="in_paste",
                label_visibility="collapsed",
                placeholder="Drop in a transcript or some notes…",
            )
            if text and text.strip():
                st.session_state.pending_input = PendingInput(
                    source="paste", payload=text,
                    filename=f"text-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt",
                )

        # Action buttons — disabled until input ready
        pending = st.session_state.get("pending_input")
        ready = pending is not None
        c1, c2 = st.columns(2)
        with c1:
            txn_clicked = st.button(
                "Transcribe only",
                disabled=not ready or pending.source == "paste",
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
