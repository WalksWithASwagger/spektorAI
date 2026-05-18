"""Stage-aware retriever — picks which KB chunks each pipeline stage sees.

The full plan in ``~/.claude/plans/rag-on-kb.md`` covers the design; this
module is the integration point that ``llm._compose_kb_block`` plugs into.

Three responsibilities:

1. **Decide whether to engage** RAG vs. dump-everything (`should_engage`).
2. **Compose stage-specific queries** (transcript + augmentation string).
3. **Always-include voice anchor** so the retriever can't accidentally
   drop the user's foundational style doc when topical hits dominate.

Knobs (all env vars; UI controls land in Phase 3):
  - WF_RAG          force on/off — "1"/"true"/"on" or "0"/"false"/"off"
  - WF_RAG_TOPK     top-K chunks per stage (default 5)
  - WF_RAG_THRESHOLD auto-engage when KB has more than N chunks (default 25)
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from ..logging import get_logger
from .chunker import Chunk
from .store import KBStore

logger = get_logger(__name__)

DEFAULT_TOP_K = int(os.getenv("WF_RAG_TOPK", "5"))
AUTO_ENGAGE_THRESHOLD = int(os.getenv("WF_RAG_THRESHOLD", "25"))

# Stage augmentation: each entry is appended to the user content to bias
# retrieval toward the right kind of KB chunks. Keep these stable strings
# rather than per-call generated ones so the embedder can't drift.
STAGE_AUGMENTATIONS: Dict[str, str] = {
    "wisdom_extraction": "voice perspective worldview style insight",
    "outline_creation": "structure framing narrative arc sections",
    "social_media": "tone hooks brand voice short punchy",
    "image_prompts": "visual aesthetic style imagery composition mood",
    "article_writing": "voice tone framing examples specificity",
    "article_critique": "voice consistency brand alignment authentic style",
    "article_revise": "voice tone framing examples specificity",
}

# Filename heuristic for the "voice anchor" — the chunk we always include
# regardless of what scored top-K. Matches files whose stem contains any
# of these substrings (case-insensitive).
_VOICE_KEYWORDS = ("voice", "style", "tone", "writing", "persona")


@dataclass
class RetrievalHit:
    chunk: Chunk
    score: float
    role: str
    stage: Optional[str]
    query: str
    augmentation: str

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "stage": self.stage,
            "score": round(self.score, 6),
            "doc_name": self.chunk.doc_name,
            "section_path": self.chunk.section_path,
            "chunk_index": self.chunk.chunk_index,
            "token_count": self.chunk.token_count,
            "label": self.chunk.label,
            "query": self.query,
            "augmentation": self.augmentation,
            "excerpt": self.chunk.text.strip()[:360],
        }


def _env_flag(name: str) -> Optional[bool]:
    """Three-way: True / False / None (not set)."""
    v = os.getenv(name, "").lower()
    if v in ("1", "true", "yes", "on"):
        return True
    if v in ("0", "false", "no", "off"):
        return False
    return None


def should_engage(user: str, mode: str = "auto") -> bool:
    """Decide whether to use RAG for a given user.

    ``mode``: "auto" (default) consults env + KB size; "always" / "never"
    short-circuit. UI Phase 3 will pass this through from settings.
    """
    if mode == "always":
        return True
    if mode == "never":
        return False
    env = _env_flag("WF_RAG")
    if env is not None:
        return env
    # Auto: engage when KB is "big enough" to benefit
    try:
        store = KBStore(user)
        store.ensure_built()
        return store.chunk_count() >= AUTO_ENGAGE_THRESHOLD
    except Exception as e:
        logger.warning("should_engage probe failed for %s: %s", user, e)
        return False


def _is_voice_doc(chunk: Chunk) -> bool:
    name = chunk.doc_name.lower()
    return any(k in name for k in _VOICE_KEYWORDS)


def _full_query(query: str, stage: Optional[str]) -> tuple[str, str]:
    aug = STAGE_AUGMENTATIONS.get(stage or "", "")
    full_query = f"{query[:2000]}\n\n{aug}".strip() if aug else query[:2000]
    return full_query, aug


def retrieve(
    user: str,
    *,
    query: str,
    stage: Optional[str] = None,
    k: int = DEFAULT_TOP_K,
) -> List[Chunk]:
    """Top-K chunks for a query. Always prepends a voice anchor (top scoring
    chunk from a voice/style doc) when one exists in the KB."""
    return [hit.chunk for hit in inspect(user, query=query, stage=stage, k=k)]


def inspect(
    user: str,
    *,
    query: str,
    stage: Optional[str] = None,
    k: int = DEFAULT_TOP_K,
) -> List[RetrievalHit]:
    """Return the same retrieval set as ``retrieve`` plus scores and roles."""
    if not query:
        return []

    full_query, aug = _full_query(query, stage)

    store = KBStore(user)
    store.ensure_built()
    if store.chunk_count() == 0:
        return []

    # Pull a generous over-fetch so we have headroom to dedupe and slot
    # the voice anchor without losing topical hits.
    raw = store.search(full_query, k=k + 5)
    score_by_key = {(c.doc_name, c.chunk_index): score for c, score in raw}
    chunks = [c for c, _score in raw]

    # Voice anchor: top-scoring chunk from a voice/style doc, even if it
    # ranked below k in the raw query.
    anchor_pair: Optional[tuple[Chunk, float]] = next(
        ((c, score) for c, score in raw if _is_voice_doc(c)),
        None,
    )
    if anchor_pair is None:
        # No voice doc hit our over-fetch — try a dedicated voice-themed query.
        voice_hits = store.search("voice tone style writing perspective", k=3)
        anchor_pair = next(
            ((c, score) for c, score in voice_hits if _is_voice_doc(c)),
            None,
        )
        if anchor_pair is not None:
            chunk, score = anchor_pair
            score_by_key[(chunk.doc_name, chunk.chunk_index)] = score

    # Stitch: anchor first if present, then dedupe topical hits, cap at k+1.
    seen_keys: set[tuple[str, int]] = set()
    out: List[RetrievalHit] = []
    if anchor_pair is not None:
        anchor, score = anchor_pair
        out.append(RetrievalHit(
            chunk=anchor,
            score=score,
            role="voice_anchor",
            stage=stage,
            query=query[:2000],
            augmentation=aug,
        ))
        seen_keys.add((anchor.doc_name, anchor.chunk_index))
    for chunk in chunks:
        key = (chunk.doc_name, chunk.chunk_index)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        out.append(RetrievalHit(
            chunk=chunk,
            score=score_by_key.get(key, 0.0),
            role="context",
            stage=stage,
            query=query[:2000],
            augmentation=aug,
        ))
        if len(out) >= k + (1 if anchor_pair else 0):
            break
    return out


def format_block(chunks: List[Chunk]) -> str:
    """Render retrieved chunks in the same shape as the legacy KB block,
    so the model sees a familiar layout. Anchor (if present) gets its
    own header so the model knows it's the foundational voice doc."""
    if not chunks:
        return ""

    lines: List[str] = [
        "Use the following knowledge base excerpts to inform your analysis "
        "and match the user's style and perspective:\n"
    ]

    anchor = chunks[0] if chunks and _is_voice_doc(chunks[0]) else None
    rest = chunks[1:] if anchor is not None else chunks

    if anchor is not None:
        lines.append("## Voice anchor")
        lines.append(f"### {anchor.label}")
        lines.append(anchor.text.strip())
        lines.append("")

    if rest:
        lines.append("## Relevant context")
        for chunk in rest:
            lines.append(f"### {chunk.label}")
            lines.append(chunk.text.strip())
            lines.append("")

    lines.append(
        "When generating, weight the voice anchor for tone and style; "
        "use the relevant context for specifics. Don't fabricate quotes "
        "or claims that aren't in the source transcript or these excerpts."
    )
    return "\n".join(lines)
