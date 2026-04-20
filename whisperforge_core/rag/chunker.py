"""Knowledge-base chunker.

Splits each KB doc into retrieval-sized chunks. Two strategies:

1. **Heading-aware** (preferred for ``.md``) — split on top-3 markdown
   headings (``#`` / ``##`` / ``###``). Each chunk inherits the section
   path so the LLM sees ``Voice Guide / Tone / Punchy`` rather than an
   unlabeled blob.
2. **Sliding window** (fallback for ``.txt`` and oversized sections) —
   ~500-token windows with 50-token overlap so concepts aren't cut at
   chunk boundaries.

A "token" here is approximated as 1 word ≈ 1.3 tokens. Cheap, model-
agnostic, accurate enough for retrieval-budget math.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

# Tunables
TARGET_TOKENS = 500
OVERLAP_TOKENS = 50
MIN_CHUNK_TOKENS = 30          # discard chunks below this — they're noise
WORDS_PER_TOKEN = 1 / 1.3      # so ~650 words ≈ 500 tokens


@dataclass
class Chunk:
    """One retrievable unit of a KB document."""
    doc_name: str              # filename stem, e.g. "kk-voice-guide"
    section_path: str          # "Voice Guide / Tone / Punchy" or "" if headerless
    text: str                  # the chunk content itself
    token_count: int           # approximate
    chunk_index: int           # 0-based ordinal within the doc

    @property
    def label(self) -> str:
        """Human-readable label for prompt rendering."""
        if self.section_path:
            return f"{self.doc_name} / {self.section_path}"
        return self.doc_name


def _approx_tokens(text: str) -> int:
    return max(1, int(len(text.split()) / WORDS_PER_TOKEN))


def _sliding_window(text: str, target: int, overlap: int) -> List[str]:
    """Token-budgeted sliding window over a string. Splits on whitespace."""
    words = text.split()
    if not words:
        return []
    target_words = max(1, int(target * WORDS_PER_TOKEN))
    overlap_words = max(0, int(overlap * WORDS_PER_TOKEN))
    step = max(1, target_words - overlap_words)
    out = []
    for start in range(0, len(words), step):
        window = words[start : start + target_words]
        if not window:
            break
        out.append(" ".join(window))
        if start + target_words >= len(words):
            break
    return out


# Match `# Heading`, `## Heading`, `### Heading` only (avoid `####` H4+).
_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.MULTILINE)


def chunk_markdown(doc_name: str, content: str) -> List[Chunk]:
    """Heading-aware split. Falls back to sliding-window for any section
    that exceeds ``TARGET_TOKENS``."""
    if not content.strip():
        return []

    # Build a list of (start_offset, level, title) plus a sentinel for EOF.
    headings = [
        (m.start(), len(m.group(1)), m.group(2).strip())
        for m in _HEADING_RE.finditer(content)
    ]

    if not headings:
        # Headerless markdown — treat as plain text.
        return chunk_plain_text(doc_name, content)

    # Convert positions to (start, end) ranges + section path.
    sections: List[tuple[str, str]] = []
    path_stack: list[tuple[int, str]] = []   # [(level, title)]
    for i, (start, level, title) in enumerate(headings):
        # Pop deeper-or-equal levels from the stack
        while path_stack and path_stack[-1][0] >= level:
            path_stack.pop()
        path_stack.append((level, title))
        section_path = " / ".join(t for _, t in path_stack)

        body_start = content.find("\n", start) + 1 if "\n" in content[start:] else start
        body_end = headings[i + 1][0] if i + 1 < len(headings) else len(content)
        body = content[body_start:body_end].strip()
        if body:
            sections.append((section_path, body))

    # Now split any oversized section via sliding window. Tiny ones survive
    # as-is.
    chunks: List[Chunk] = []
    chunk_idx = 0
    for section_path, body in sections:
        toks = _approx_tokens(body)
        if toks <= TARGET_TOKENS:
            if toks >= MIN_CHUNK_TOKENS:
                chunks.append(Chunk(
                    doc_name=doc_name, section_path=section_path,
                    text=body, token_count=toks, chunk_index=chunk_idx,
                ))
                chunk_idx += 1
        else:
            for piece in _sliding_window(body, TARGET_TOKENS, OVERLAP_TOKENS):
                ptok = _approx_tokens(piece)
                if ptok >= MIN_CHUNK_TOKENS:
                    chunks.append(Chunk(
                        doc_name=doc_name, section_path=section_path,
                        text=piece, token_count=ptok, chunk_index=chunk_idx,
                    ))
                    chunk_idx += 1
    return chunks


def chunk_plain_text(doc_name: str, content: str) -> List[Chunk]:
    """Sliding-window split with no section paths. Used for ``.txt`` and
    headerless ``.md``."""
    if not content.strip():
        return []
    chunks: List[Chunk] = []
    for i, piece in enumerate(_sliding_window(content, TARGET_TOKENS, OVERLAP_TOKENS)):
        toks = _approx_tokens(piece)
        if toks >= MIN_CHUNK_TOKENS:
            chunks.append(Chunk(
                doc_name=doc_name, section_path="",
                text=piece, token_count=toks, chunk_index=i,
            ))
    return chunks


def chunk_file(path: Path) -> List[Chunk]:
    """Dispatch by file extension."""
    text = path.read_text(encoding="utf-8")
    name = path.stem
    if path.suffix.lower() == ".md":
        return chunk_markdown(name, text)
    return chunk_plain_text(name, text)


def chunk_kb_dir(kb_dir: Path) -> List[Chunk]:
    """Walk a knowledge_base/ directory and chunk every .md/.txt file
    inside. Files are processed in sorted order for stable ordinals
    across rebuilds."""
    if not kb_dir.exists():
        return []
    out: List[Chunk] = []
    for path in sorted(kb_dir.iterdir()):
        if path.suffix.lower() in {".md", ".txt"} and not path.name.startswith("."):
            out.extend(chunk_file(path))
    return out
