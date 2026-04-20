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

/* Bordered cards (st.container(border=True)) — Streamlit applies an
   inline border style to the underlying stVerticalBlock; we match
   on that so our soft-purple border replaces the default white one.
   The :has() selector is supported in Safari/Firefox/Chrome since 2023. */
[data-testid="stVerticalBlock"]:has(> div[style*="border"]),
div[data-testid="stVerticalBlock"][style*="border"] {
    border: 1px solid rgba(121, 40, 202, 0.2) !important;
    border-radius: var(--card-radius) !important;
}
/* Fallback: any vertical block that Streamlit bordered gets a gradient
   background, echoing the old .content-section treatment. */
div[data-testid="stVerticalBlock"] > div[style*="border: 1px solid"] {
    border-color: rgba(121, 40, 202, 0.25) !important;
    border-radius: var(--card-radius) !important;
    background: linear-gradient(
        160deg,
        rgba(26, 26, 36, 0.55) 0%,
        rgba(18, 18, 24, 0.55) 100%
    ) !important;
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
}

/* Segmented control — Streamlit 1.56 renders this as stButtonGroup,
   NOT stSegmentedControl. Verified via the frontend JS bundle. */
[data-testid="stButtonGroup"] button {
    background: transparent !important;
    border: 1px solid rgba(121, 40, 202, 0.15) !important;
    color: var(--text-secondary) !important;
    font-size: 0.8rem !important;
    transition: all 0.2s ease;
}
[data-testid="stButtonGroup"] button:hover {
    border-color: rgba(121, 40, 202, 0.35) !important;
    color: var(--text-primary) !important;
}
[data-testid="stButtonGroup"] button[aria-pressed="true"],
[data-testid="stButtonGroup"] button[data-selected="true"] {
    background: linear-gradient(
        110deg,
        rgba(121, 40, 202, 0.3) 0%,
        rgba(255, 0, 128, 0.12) 100%
    ) !important;
    border-color: rgba(121, 40, 202, 0.55) !important;
    color: var(--text-primary) !important;
    box-shadow: 0 0 10px rgba(121, 40, 202, 0.25);
}

/* st.status container — shares the stExpander testid in current
   Streamlit builds. Applying both is harmless. */
[data-testid="stStatusWidget"],
[data-testid="stExpander"] {
    border-radius: var(--card-radius) !important;
    border: 1px solid rgba(121, 40, 202, 0.2) !important;
    background: rgba(18, 18, 24, 0.65) !important;
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

/* ────────────────────────────────────────────────────────────────
   Restored / enhanced vibe details (0.6.1)
   ──────────────────────────────────────────────────────────────── */

/* Scanner line — restored from the old UI. Made it 2px thick + brighter
   glow so it actually reads on screen. Sweeps top→bottom every 10s. */
.scanner-line {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(
        90deg,
        transparent 0%,
        rgba(121, 40, 202, 0.15) 20%,
        var(--accent-primary) 50%,
        rgba(121, 40, 202, 0.15) 80%,
        transparent 100%
    );
    box-shadow: 0 0 12px rgba(121, 40, 202, 0.5),
                0 0 24px rgba(255, 0, 128, 0.2);
    opacity: 0.8;
    z-index: 9999;
    pointer-events: none;
    animation: scanner-sweep 10s linear infinite;
}

@keyframes scanner-sweep {
    0%   { top: -4px;    opacity: 0; }
    6%   {                opacity: 0.9; }
    94%  {                opacity: 0.9; }
    100% { top: 100vh;    opacity: 0; }
}

/* Ambient background drift — subtle hue shift on the app canvas so the
   page feels alive without being distracting. */
.stApp {
    background: linear-gradient(
        160deg,
        var(--bg-primary) 0%,
        #12101f 50%,
        #0f0f17 100%
    );
    background-size: 100% 140%;
    animation: ambient-drift 60s ease-in-out infinite alternate;
}

@keyframes ambient-drift {
    0%   { background-position: 0% 0%; }
    100% { background-position: 0% 100%; }
}

/* Primary buttons (type="primary") — replaces the old .lucky-button.
   Teal-purple gradient with a slow animated sheen so the "I'm feeling
   lucky" + "Save to Notion" buttons read as the main action. */
.stButton > button[kind="primary"] {
    background: linear-gradient(
        110deg,
        rgba(54, 211, 153, 0.2) 0%,
        rgba(121, 40, 202, 0.3) 50%,
        rgba(255, 0, 128, 0.2) 100%
    ) !important;
    background-size: 200% 100%;
    border: 1px solid rgba(121, 40, 202, 0.55) !important;
    box-shadow: 0 0 14px rgba(121, 40, 202, 0.2);
    animation: primary-sheen 6s ease-in-out infinite;
    font-weight: 600 !important;
}

.stButton > button[kind="primary"]:hover {
    background-position: 100% 0% !important;
    box-shadow: 0 0 22px rgba(121, 40, 202, 0.35),
                0 0 38px rgba(255, 0, 128, 0.18);
    transform: translateY(-1px);
}

@keyframes primary-sheen {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

/* Section-header underline wipes in on first render. */
.section-header::after {
    transform-origin: left;
    animation: underline-wipe 0.6s ease-out both;
}
@keyframes underline-wipe {
    from { transform: scaleX(0); }
    to   { transform: scaleX(1); }
}

/* sac.steps — make the active step pulse (borrowed the old @keyframes
   pulse that was on .process-indicator .dot before it got pruned). */
.ant-steps-item-process .ant-steps-item-icon {
    animation: step-pulse 2s ease-in-out infinite;
}
@keyframes step-pulse {
    0%, 100% { box-shadow: 0 0 8px rgba(121, 40, 202, 0.3); }
    50%      { box-shadow: 0 0 18px rgba(121, 40, 202, 0.6),
                           0 0 26px rgba(255, 0, 128, 0.25); }
}

/* Bottom bar — top edge glow + subtle shimmer line. */
.bottom-bar::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(
        90deg,
        transparent 0%,
        rgba(121, 40, 202, 0.5) 30%,
        rgba(255, 0, 128, 0.5) 70%,
        transparent 100%
    );
    animation: bottom-shimmer 8s ease-in-out infinite;
}
.bottom-bar { position: relative; }
@keyframes bottom-shimmer {
    0%, 100% { opacity: 0.4; }
    50%      { opacity: 1.0; }
}

/* Bordered-container hover lift — echoes the old .quick-button feel but
   applied to the main content cards (st.container(border=True)). */
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: rgba(121, 40, 202, 0.35) !important;
    box-shadow: 0 6px 28px rgba(0, 0, 0, 0.35),
                0 0 0 1px rgba(121, 40, 202, 0.12);
    transition: border-color 0.3s ease, box-shadow 0.3s ease;
}
</style>

<!-- Scanner line injected alongside the stylesheet so it's always on the page. -->
<div class="scanner-line"></div>
"""
