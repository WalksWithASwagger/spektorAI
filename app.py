"""WhisperForge entrypoint — three-zone Streamlit shell.

The heavy lifting lives in two places:
- ``whisperforge_core`` — pure-logic package (no Streamlit imports): audio,
  llm, notion, pipeline, adapters, cost, history, images, prompts.
- ``ui/`` — presentation layer, split by concern: session state, shell
  chrome, sidebar, input card, pipeline card, output card, dialogs.

This file's only job is to compose them. v0.6.0 moved everything that used
to be inline here into those modules; app.py shrunk from ~970 LoC to ~80.
"""

from __future__ import annotations

import streamlit as st
from dotenv import load_dotenv

import styles
from ui import input as input_card
from ui import output as output_card
from ui import pipeline as pipeline_card
from ui import session
from ui import shell
from ui import sidebar

load_dotenv()

st.set_page_config(
    page_title="WhisperForge",
    page_icon=":material/graphic_eq:",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
    # 1. Apply the cyberpunk theme (preserved from 0.5.0).
    st.markdown(styles.CSS, unsafe_allow_html=True)

    # 2. Initialize every session_state key we'll read anywhere in the UI.
    session.init_all_state()

    # 3. Three-zone render: header / sidebar + main / bottom bar.
    shell.render_header()
    sidebar.render()

    input_card.render()
    pipeline_card.render()
    output_card.render()

    shell.render_bottom_bar()


if __name__ == "__main__":
    main()
