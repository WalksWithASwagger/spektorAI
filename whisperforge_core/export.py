"""Export a ContentBundle to markdown.

Mirrors the Notion rendering but produces a single .md file with YAML
frontmatter — Obsidian-compatible, Marked-compatible, readable in any
plain-text editor. Useful when you want a pipeline run in a local vault
or git repo instead of (or alongside) Notion.

Callers feed a ``notion.ContentBundle`` in and get either the string
content or a written file path back.
"""

from __future__ import annotations

import re
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import CACHE_DIR
from .logging import get_logger
from .notion import ContentBundle

logger = get_logger(__name__)

DEFAULT_EXPORT_DIR = CACHE_DIR / "exports"


def _slugify(text: str, max_len: int = 60) -> str:
    """Filesystem-safe slug from a title string."""
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
    return slug[:max_len] or "untitled"


def _yaml_frontmatter(bundle: ContentBundle, extra: Optional[dict] = None) -> str:
    """Produce Obsidian-style YAML frontmatter. Tags become a list; the
    rest stay as scalars. Keeps the block short + scannable."""
    fm: dict = {
        "title": bundle.title,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    if bundle.audio_filename:
        fm["source"] = bundle.audio_filename
    if bundle.models_used:
        fm["models"] = bundle.models_used
    if bundle.tags:
        fm["tags"] = bundle.tags
    if extra:
        fm.update(extra)

    lines = ["---"]
    for key, val in fm.items():
        if isinstance(val, list):
            lines.append(f"{key}:")
            for item in val:
                lines.append(f"  - {item}")
        else:
            # Escape strings containing YAML-dangerous chars.
            val_s = str(val).replace("\n", " ").strip()
            if any(c in val_s for c in [":", "#", "'", '"']):
                val_s = val_s.replace('"', '\\"')
                val_s = f'"{val_s}"'
            lines.append(f"{key}: {val_s}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _timestamp_prefix(seconds) -> str:
    """Format [MM:SS] or [H:MM:SS] for chapter bullets."""
    if not isinstance(seconds, (int, float)):
        return ""
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"[{h}:{m:02d}:{sec:02d}] " if h else f"[{m}:{sec:02d}] "


def markdown_from_bundle(bundle: ContentBundle,
                        *, notion_url: Optional[str] = None) -> str:
    """Render the bundle as a full markdown document string.

    Order mirrors the Notion page for familiarity: summary → chapters →
    transcript → wisdom → socials → image prompts → outline → article →
    revision notes → fact check → image filenames → metadata footer.
    """
    extra_fm = {}
    if notion_url:
        extra_fm["notion_url"] = notion_url
    parts: list[str] = [_yaml_frontmatter(bundle, extra=extra_fm)]

    parts.append(f"# {bundle.title}\n")

    if bundle.summary:
        parts.append(f"> {bundle.summary}\n")

    if bundle.chapters:
        parts.append("## Chapters\n")
        for c in bundle.chapters:
            prefix = _timestamp_prefix(c.get("start_seconds"))
            title = (c.get("title") or "").strip() or "(untitled)"
            summary = (c.get("summary") or "").strip()
            line = f"- {prefix}**{title}**"
            if summary:
                line += f" — {summary}"
            parts.append(line)
        parts.append("")

    def _section(heading: str, body: Optional[str]) -> None:
        if body and body.strip():
            parts.append(f"## {heading}\n")
            parts.append(body.strip())
            parts.append("")

    _section("Transcription", bundle.transcript)
    _section("Wisdom", bundle.wisdom)
    _section("Socials", bundle.social_content)
    _section("Image prompts", bundle.image_prompts)
    _section("Outline", bundle.outline)
    _section("Article", bundle.article)

    if bundle.article_critique:
        parts.append("## Revision notes\n")
        parts.append(bundle.article_critique.strip())
        parts.append("")

    if bundle.fact_check_ran:
        if bundle.fact_check_flags:
            parts.append("## Fact check — flags\n")
            for f in bundle.fact_check_flags:
                parts.append(
                    f"- **Claim:** {f.get('claim', '')}\n"
                    f"  **Issue:** {f.get('issue', '')}"
                )
            parts.append("")
        else:
            parts.append("## Fact check\n")
            parts.append("✅ No claims flagged — article grounded in source.")
            parts.append("")

    if bundle.audio_filename:
        parts.append("## Metadata\n")
        parts.append(f"- **Original audio:** {bundle.audio_filename}")
        if bundle.models_used:
            parts.append(f"- **Models used:** {', '.join(bundle.models_used)}")
        if notion_url:
            parts.append(f"- **Notion page:** [{notion_url}]({notion_url})")
        parts.append("")

    return "\n".join(parts).rstrip() + "\n"


def export(
    bundle: ContentBundle,
    *,
    out_dir: Optional[Path] = None,
    notion_url: Optional[str] = None,
    overwrite: bool = False,
) -> Path:
    """Write the markdown rendering of ``bundle`` to disk. Filename is
    ``YYYY-MM-DD-<title-slug>.md``. Returns the path actually written.

    Defaults ``out_dir`` to ``.cache/exports/`` unless overridden (e.g. to
    an Obsidian vault folder).
    """
    target_dir = Path(out_dir) if out_dir else DEFAULT_EXPORT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    date = datetime.now().strftime("%Y-%m-%d")
    slug = _slugify(bundle.title)
    target = target_dir / f"{date}-{slug}.md"

    if target.exists() and not overwrite:
        # Disambiguate with a short timestamp suffix so we never clobber a
        # prior export of the same title on the same day.
        target = target_dir / f"{date}-{slug}-{datetime.now():%H%M%S}.md"

    content = markdown_from_bundle(bundle, notion_url=notion_url)
    target.write_text(content, encoding="utf-8")
    logger.info("exported markdown (%d chars) → %s", len(content), target)
    return target
