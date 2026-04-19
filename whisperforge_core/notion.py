"""Notion export.

Builds a structured Notion page from a ContentBundle of generated materials.
Honors Notion's 2000-char-per-paragraph-block limit via a 1900-char chunker
(kept under cap for safety). Pure logic — no Streamlit imports.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from notion_client import Client

from .config import NOTION_API_KEY, NOTION_DATABASE_ID
from .logging import get_logger

logger = get_logger(__name__)

# Notion rejects > 2000 chars in a single rich_text block. 1900 keeps headroom.
NOTION_CHUNK_SIZE = 1900


@dataclass
class ContentBundle:
    """Everything that gets saved to a single Notion page.

    ``title`` is the page name; other fields are optional so Text-input flows
    can skip audio-specific pieces.
    """

    title: str
    transcript: str = ""
    wisdom: str = ""
    outline: str = ""
    social_content: str = ""
    image_prompts: str = ""
    article: str = ""
    summary: str = ""
    tags: List[str] = field(default_factory=list)
    audio_filename: Optional[str] = None
    models_used: List[str] = field(default_factory=list)


def _client() -> Client:
    return Client(auth=NOTION_API_KEY)


def chunk_text_for_notion(text: str, chunk_size: int = NOTION_CHUNK_SIZE) -> List[str]:
    """Split text into chunks that respect Notion's per-block character limit."""
    if not text:
        return []
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


def _paragraph(content: str) -> dict:
    return {
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": content}}]},
    }


def _toggle_section(label: str, color: str, body: str) -> dict:
    return {
        "type": "toggle",
        "toggle": {
            "rich_text": [{"type": "text", "text": {"content": label}}],
            "color": color,
            "children": [_paragraph(chunk) for chunk in chunk_text_for_notion(body)],
        },
    }


def estimate_tokens(bundle: ContentBundle) -> int:
    """Rough token estimate (4 chars/token) plus system-prompt overhead."""
    total = 0
    for piece in (
        bundle.transcript,
        bundle.wisdom,
        bundle.outline,
        bundle.social_content,
        bundle.image_prompts,
        bundle.article,
    ):
        if piece:
            total += len(piece) / 4
    return int(total + 1000)


def build_blocks(bundle: ContentBundle) -> List[dict]:
    """Build the ordered block list for a Notion page from a ContentBundle."""
    blocks: List[dict] = []

    if bundle.summary:
        blocks.append(
            {
                "type": "callout",
                "callout": {
                    "rich_text": [{"type": "text", "text": {"content": bundle.summary}}],
                    "color": "purple_background",
                    "icon": {"type": "emoji", "emoji": "💜"},
                },
            }
        )
        blocks.append({"type": "divider", "divider": {}})

    if bundle.transcript:
        blocks.append(_toggle_section("Transcription", "default", bundle.transcript))
    if bundle.wisdom:
        blocks.append(_toggle_section("Wisdom", "brown_background", bundle.wisdom))
    if bundle.social_content:
        blocks.append(_toggle_section("Socials", "orange_background", bundle.social_content))
    if bundle.image_prompts:
        blocks.append(_toggle_section("Image Prompts", "green_background", bundle.image_prompts))
    if bundle.outline:
        blocks.append(_toggle_section("Outline", "blue_background", bundle.outline))
    if bundle.article:
        blocks.append(_toggle_section("Draft Post", "purple_background", bundle.article))

    if bundle.audio_filename:
        blocks.append(
            {
                "type": "toggle",
                "toggle": {
                    "rich_text": [{"type": "text", "text": {"content": "Original Audio"}}],
                    "color": "red_background",
                    "children": [_paragraph(bundle.audio_filename)],
                },
            }
        )

    # Metadata footer
    blocks.append({"type": "divider", "divider": {}})
    blocks.append(
        {
            "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Metadata"}}]},
        }
    )
    blocks.append(_paragraph(f"**Original Audio:** {bundle.audio_filename or 'None'}"))
    blocks.append(_paragraph(f"**Created:** {datetime.now().strftime('%Y-%m-%d %H:%M')}"))
    blocks.append(
        _paragraph(
            f"**Models Used:** {', '.join(bundle.models_used) if bundle.models_used else 'None'}"
        )
    )
    blocks.append(_paragraph(f"**Estimated Tokens:** {estimate_tokens(bundle):,}"))

    return blocks


def create_page(bundle: ContentBundle, database_id: Optional[str] = None) -> Optional[str]:
    """Create a Notion page from the bundle. Returns the page URL or None on failure."""
    db = database_id or NOTION_DATABASE_ID
    if not db:
        logger.error("Notion database_id not configured")
        return None

    blocks = build_blocks(bundle)
    properties = {
        "Name": {"title": [{"text": {"content": bundle.title}}]},
    }
    if bundle.tags:
        properties["Tags"] = {"multi_select": [{"name": tag} for tag in bundle.tags]}

    try:
        response = _client().pages.create(
            parent={"database_id": db},
            properties=properties,
            children=blocks,
        )
    except Exception as e:
        logger.error("Notion page creation failed: %s", e)
        return None

    if isinstance(response, dict) and "id" in response:
        page_id = response["id"].replace("-", "")
        return f"https://notion.so/{page_id}"
    logger.error("Notion API returned unexpected response: %r", response)
    return None
