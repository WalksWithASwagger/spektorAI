"""CSS for the WhisperForge Streamlit UI.

Extracted from the former local_css() blob in app.py. Kept as a plain string
constant so the app.py import footprint stays tiny and this file can be edited
without scrolling through 2000+ lines of Python.
"""

CSS = """
<style>
/* Refined Cyberpunk Theme - WhisperForge Command Center */

/* Base variables for limited color palette */
:root {
    --bg-primary: #121218;
    --bg-secondary: #1a1a24;
    --bg-tertiary: #222230;
    --accent-primary: #7928CA;
    --accent-secondary: #FF0080;
    --text-primary: #f0f0f0;
    --text-secondary: #a0a0a0;
    --text-muted: #707070;
    --success: #36D399;
    --warning: #FBBD23;
    --error: #F87272;
    --info: #3ABFF8;
    --border-radius: 6px;
    --card-radius: 10px;
    --glow-intensity: 4px;
    --terminal-font: 'JetBrains Mono', 'Courier New', monospace;
    --system-font: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
}

/* Global styles */
.stApp {
    background: linear-gradient(160deg, var(--bg-primary) 0%, #0f0f17 100%);
    color: var(--text-primary);
    font-family: var(--system-font);
}

/* Clean, compact header */
.header-container {
    border-radius: var(--card-radius);
    background: linear-gradient(110deg, rgba(121, 40, 202, 0.10) 0%, rgba(0, 0, 0, 0) 80%);
    border: 1px solid rgba(121, 40, 202, 0.25);
    padding: 12px 20px;
    margin-bottom: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    position: relative;
    overflow: hidden;
}

.header-container::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(121, 40, 202, 0.5), transparent);
    animation: header-shine 3s ease-in-out infinite;
}

@keyframes header-shine {
    0% { transform: translateX(-100%); }
    50% { transform: translateX(100%); }
    100% { transform: translateX(-100%); }
}

.header-title {
    font-family: var(--terminal-font);
    font-size: 1.4rem;
    font-weight: 500;
    background: linear-gradient(90deg, #7928CA, #FF0080);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: 0.02em;
}

.header-date {
    font-family: var(--terminal-font);
    color: var(--text-secondary);
    font-size: 0.85rem;
    opacity: 0.8;
}

/* Section headers with subtle underline */
.section-header {
    color: var(--text-primary);
    font-size: 0.9rem;
    font-weight: 600;
    margin: 20px 0 8px 0;
    padding-bottom: 6px;
    position: relative;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

.section-header::after {
    content: "";
    position: absolute;
    left: 0;
    bottom: 0;
    height: 1px;
    width: 100%;
    background: linear-gradient(90deg, var(--accent-primary), transparent);
}

/* Tabs styling */
.stTabs [data-baseweb="tab-list"] {
    background-color: var(--bg-secondary);
    border-radius: var(--border-radius);
    padding: 4px;
    border: 1px solid rgba(255, 255, 255, 0.05);
    gap: 2px;
}

.stTabs [data-baseweb="tab"] {
    border-radius: var(--border-radius);
    color: var(--text-secondary);
    background-color: transparent;
    transition: all 0.2s ease;
    font-size: 0.85rem;
    font-weight: 500;
    padding: 8px 16px;
}

.stTabs [data-baseweb="tab"]:hover {
    color: var(--text-primary);
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(110deg, rgba(121, 40, 202, 0.15) 0%, rgba(255, 0, 128, 0.05) 100%);
    color: var(--text-primary) !important;
    border: 1px solid rgba(121, 40, 202, 0.25) !important;
}

/* File uploader styling */
[data-testid="stFileUploader"] {
    background: linear-gradient(120deg, var(--bg-secondary) 0%, var(--bg-tertiary) 100%);
    border: 1px dashed rgba(121, 40, 202, 0.3);
    border-radius: var(--card-radius);
    padding: 15px;
    transition: all 0.2s ease;
}

[data-testid="stFileUploader"]:hover {
    border-color: rgba(121, 40, 202, 0.5);
    box-shadow: 0 0 15px rgba(121, 40, 202, 0.15);
}

/* Button styling */
.stButton > button {
    background: linear-gradient(110deg, rgba(121, 40, 202, 0.08) 0%, rgba(255, 0, 128, 0.05) 100%);
    border: 1px solid rgba(121, 40, 202, 0.25);
    color: var(--text-primary);
    border-radius: var(--border-radius);
    padding: 8px 16px;
    font-family: var(--system-font);
    transition: all 0.2s ease;
    font-weight: 500;
    font-size: 0.85rem;
}

.stButton > button:hover {
    background: linear-gradient(110deg, rgba(121, 40, 202, 0.15) 0%, rgba(255, 0, 128, 0.08) 100%);
    border-color: rgba(121, 40, 202, 0.4);
    transform: translateY(-1px);
    box-shadow: 0 3px 10px rgba(0, 0, 0, 0.15);
}

.stButton > button:active {
    transform: translateY(0px);
}

/* Primary button emphasis — applied by type="primary" */
.stButton > button[kind="primary"] {
    background: linear-gradient(110deg, rgba(121, 40, 202, 0.25) 0%, rgba(255, 0, 128, 0.12) 100%);
    border-color: rgba(121, 40, 202, 0.5);
    box-shadow: 0 0 12px rgba(121, 40, 202, 0.15);
}

.stButton > button[kind="primary"]:hover {
    background: linear-gradient(110deg, rgba(121, 40, 202, 0.35) 0%, rgba(255, 0, 128, 0.18) 100%);
    border-color: rgba(121, 40, 202, 0.7);
    box-shadow: 0 0 18px rgba(121, 40, 202, 0.25);
}

/* Audio player styling */
audio {
    width: 100%;
    border-radius: var(--border-radius);
    background: var(--bg-secondary);
    margin: 10px 0;
    height: 32px;
}

/* Text area styling */
.stTextArea > div > div > textarea {
    background-color: var(--bg-secondary);
    color: var(--text-primary);
    border: 1px solid rgba(121, 40, 202, 0.2);
    border-radius: var(--border-radius);
    padding: 10px;
    font-family: var(--system-font);
}

.stTextArea > div > div > textarea:focus {
    border: 1px solid rgba(121, 40, 202, 0.4);
    box-shadow: 0 0 0 1px rgba(121, 40, 202, 0.2);
}

/* Text input styling */
.stTextInput > div > div > input {
    background-color: var(--bg-secondary);
    color: var(--text-primary);
    border: 1px solid rgba(121, 40, 202, 0.2);
    border-radius: var(--border-radius);
    padding: 8px 12px;
    font-family: var(--system-font);
    height: 36px;
}

.stTextInput > div > div > input:focus {
    border: 1px solid rgba(121, 40, 202, 0.4);
    box-shadow: 0 0 0 1px rgba(121, 40, 202, 0.2);
}

/* Selectbox styling */
.stSelectbox > div {
    background-color: var(--bg-secondary);
}

.stSelectbox > div > div {
    background-color: var(--bg-secondary);
    color: var(--text-primary);
    border: 1px solid rgba(121, 40, 202, 0.2);
    border-radius: var(--border-radius);
}

/* Progress bar styling */
.stProgress > div > div > div {
    background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
    border-radius: var(--border-radius);
}

/* Expander styling */
.streamlit-expanderHeader {
    background-color: var(--bg-secondary);
    border-radius: var(--border-radius);
    border: 1px solid rgba(121, 40, 202, 0.1);
    font-size: 0.85rem;
    padding: 8px 12px;
}

.streamlit-expanderHeader:hover {
    border-color: rgba(121, 40, 202, 0.25);
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background-color: var(--bg-primary);
    border-right: 1px solid rgba(121, 40, 202, 0.15);
}

[data-testid="stSidebar"] [data-testid="stMarkdown"] h1,
[data-testid="stSidebar"] [data-testid="stMarkdown"] h2,
[data-testid="stSidebar"] [data-testid="stMarkdown"] h3 {
    color: var(--accent-primary);
    font-size: 1rem;
}

/* ────────────────────────────────────────────────────────────────
   0.6.0 three-zone refactor additions
   ──────────────────────────────────────────────────────────────── */

/* Bordered cards (st.container(border=True)) — soften the default white
   border to match the brand palette. */
[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid rgba(121, 40, 202, 0.15) !important;
    border-radius: var(--card-radius) !important;
    background: linear-gradient(
        160deg,
        rgba(26, 26, 36, 0.6) 0%,
        rgba(18, 18, 24, 0.6) 100%
    );
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
}

/* Segmented control (sidebar provider picker) — echo the pill-button
   gradient so the chrome feels consistent. */
[data-testid="stSegmentedControl"] button {
    background: transparent !important;
    border: 1px solid rgba(121, 40, 202, 0.15) !important;
    color: var(--text-secondary) !important;
    font-size: 0.8rem !important;
}
[data-testid="stSegmentedControl"] button[aria-pressed="true"] {
    background: linear-gradient(110deg, rgba(121, 40, 202, 0.25) 0%, rgba(255, 0, 128, 0.1) 100%) !important;
    border-color: rgba(121, 40, 202, 0.5) !important;
    color: var(--text-primary) !important;
    box-shadow: 0 0 8px rgba(121, 40, 202, 0.2);
}

/* st.status container — keep it from taking over the page */
[data-testid="stStatusWidget"] {
    border-radius: var(--card-radius) !important;
    border: 1px solid rgba(121, 40, 202, 0.2) !important;
    background: rgba(18, 18, 24, 0.7);
}

/* sac.steps — recolor the AntD defaults to match our palette */
.ant-steps-item-icon {
    background: rgba(121, 40, 202, 0.15) !important;
    border-color: rgba(121, 40, 202, 0.3) !important;
}
.ant-steps-item-process .ant-steps-item-icon {
    background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary)) !important;
    border-color: transparent !important;
    box-shadow: 0 0 10px rgba(121, 40, 202, 0.4);
}
.ant-steps-item-finish .ant-steps-item-icon {
    background: rgba(54, 211, 153, 0.15) !important;
    border-color: var(--success) !important;
}
.ant-steps-item-finish .ant-steps-icon {
    color: var(--success) !important;
}

/* Sidebar status footer — compact dot row replacing the old app-footer */
.sidebar-status {
    margin-top: 24px;
    padding-top: 12px;
    border-top: 1px solid rgba(121, 40, 202, 0.12);
    font-size: 0.72rem;
    color: var(--text-muted);
    text-align: center;
    letter-spacing: 0.03em;
}

/* Colored status dots (reused inline in the sidebar footer) */
.status-dot {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    margin: 0 2px 0 4px;
    vertical-align: middle;
}
.status-dot.status-secure       { background: var(--success);         box-shadow: 0 0 5px var(--success); }
.status-dot.status-sovereignty  { background: var(--accent-primary);  box-shadow: 0 0 5px var(--accent-primary); }
.status-dot.status-offline      { background: var(--info);            box-shadow: 0 0 5px var(--info); }

/* Bottom bar — pinned via streamlit-extras bottom_container. The library
   handles positioning; we handle the look. */
.bottom-bar {
    border-top: 1px solid rgba(121, 40, 202, 0.25);
    padding: 10px 14px 2px 14px;
    background: linear-gradient(
        180deg,
        rgba(18, 18, 24, 0.85) 0%,
        rgba(12, 12, 18, 0.95) 100%
    );
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    font-family: var(--terminal-font);
}

.bottom-metric {
    display: flex;
    flex-direction: column;
    gap: 1px;
    padding: 2px 6px;
}
.bottom-label {
    font-size: 0.65rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
.bottom-value {
    font-size: 0.95rem;
    color: var(--text-primary);
    font-weight: 500;
    font-family: var(--terminal-font);
}

/* Dialog modal — soften the default border, match palette */
[data-testid="stDialog"] > div {
    background: linear-gradient(160deg, var(--bg-secondary) 0%, var(--bg-primary) 100%) !important;
    border: 1px solid rgba(121, 40, 202, 0.3) !important;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
}

/* Popover (sidebar ⚙ More uses these) */
[data-testid="stPopover"] {
    background: var(--bg-secondary) !important;
    border: 1px solid rgba(121, 40, 202, 0.25) !important;
    border-radius: var(--card-radius) !important;
}

/* Feedback widgets (thumbs on output sections) — subtle, not neon */
[data-testid="stFeedback"] button {
    background: transparent !important;
    color: var(--text-muted) !important;
    border: 1px solid rgba(121, 40, 202, 0.1) !important;
}
[data-testid="stFeedback"] button[aria-pressed="true"] {
    color: var(--accent-primary) !important;
    border-color: rgba(121, 40, 202, 0.4) !important;
}
</style>
"""
