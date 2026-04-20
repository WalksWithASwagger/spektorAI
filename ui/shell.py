"""Three-zone app shell: header, sidebar wrapper, and bottom status bar.

The sidebar content itself lives in ``ui/sidebar.py``. This module owns the
chrome — the header row with the title and timestamp, and the bottom bar
that shows live cost + session metadata. Bottom bar is fragment-polled
every 2 s so it updates during a run without forcing the rest of the page
to rerender.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st
from streamlit_extras.bottom_container import bottom

from whisperforge_core import cost

from . import session as session_mod

_DATE_FMT = "%a %d %b %Y · %H:%M"


def render_header() -> None:
    """The gradient-text title row. Preserves the existing .header-container
    styling from styles.py (the load-bearing aesthetic)."""
    now = datetime.now().strftime(_DATE_FMT)
    st.markdown(
        f"""
        <div class="header-container">
            <div class="header-title">WhisperForge // Control_Center</div>
            <div class="header-date">{now}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.fragment(run_every="2s")
def _bottom_bar_fragment() -> None:
    """Poll the cost ledger every 2 s without rerunning the whole app."""
    b = cost.estimate_cost()
    provider = st.session_state.get("ai_provider", "—")
    model = st.session_state.get("ai_model", "—")
    cols = st.columns([2, 2, 2, 3, 2])
    cols[0].markdown(
        f"<div class='bottom-metric'><span class='bottom-label'>Cost</span>"
        f"<span class='bottom-value'>${b.total_usd:.4f}</span></div>",
        unsafe_allow_html=True,
    )
    cols[1].markdown(
        f"<div class='bottom-metric'><span class='bottom-label'>Calls</span>"
        f"<span class='bottom-value'>{b.calls}</span></div>",
        unsafe_allow_html=True,
    )
    cols[2].markdown(
        f"<div class='bottom-metric'><span class='bottom-label'>Cache saved</span>"
        f"<span class='bottom-value'>${b.cache_savings_usd:.4f}</span></div>",
        unsafe_allow_html=True,
    )
    cols[3].markdown(
        f"<div class='bottom-metric'><span class='bottom-label'>Model</span>"
        f"<span class='bottom-value'>{provider} · {model}</span></div>",
        unsafe_allow_html=True,
    )
    with cols[4]:
        if st.button("Clear run", key="bottom_clear_run", use_container_width=True,
                     disabled=not session_mod.has_output()):
            session_mod.clear_run()
            st.toast("Run cleared.", icon=":material/restart_alt:")
            st.rerun()


def render_bottom_bar() -> None:
    """Fixed bottom container wrapping the fragment. streamlit-extras'
    ``bottom()`` pins this to the viewport bottom via CSS."""
    with bottom():
        st.markdown("<div class='bottom-bar'>", unsafe_allow_html=True)
        _bottom_bar_fragment()
        st.markdown("</div>", unsafe_allow_html=True)
