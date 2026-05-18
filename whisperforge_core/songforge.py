"""Text-first SongForge materials from captures and KB context."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping
from typing import Any

SAFETY_NOTE = (
    "Original lyrics only. Use supplied transcript and KB material as source "
    "context; do not imitate living artists or interpolate copyrighted lyrics."
)

_STOPWORDS = {
    "about", "after", "again", "also", "because", "been", "being", "between",
    "could", "every", "from", "have", "into", "just", "more", "most", "need",
    "only", "people", "really", "should", "something", "their", "there",
    "these", "thing", "this", "through", "want", "were", "when", "where",
    "which", "while", "with", "would", "your",
}
_ARC_LABELS = ("Opening tension", "Turn", "Resolution")


def build_pack(
    transcript: str,
    knowledge_base: Mapping[str, str] | None = None,
    *,
    title: str = "SongForge draft",
) -> dict[str, Any]:
    """Build deterministic song-ready materials from source text.

    This is intentionally local and credential-free. LLM polish can sit on top
    later, but the first contract is stable shape, source notes, and no artist
    imitation.
    """
    transcript = _normalize(transcript)
    kb_notes = _kb_notes(knowledge_base or {})
    kb_text = " ".join(note["excerpt"] for note in kb_notes)
    source_text = " ".join(part for part in (transcript, kb_text) if part)
    themes = _themes(source_text)
    motifs = _motifs(source_text, themes)
    phrases = _phrases(transcript)
    emotional_arc = _emotional_arc(transcript, themes)
    source_notes = _source_notes(transcript, kb_notes, themes)
    return {
        "title": title,
        "mode": "songforge",
        "safety_note": SAFETY_NOTE,
        "themes": themes,
        "motifs": motifs,
        "phrases": phrases,
        "emotional_arc": emotional_arc,
        "lyric_draft": _lyric_draft(themes, motifs, phrases),
        "spoken_word": _spoken_word(themes, motifs, emotional_arc),
        "music_prompt_pack": _music_prompt_pack(themes, motifs, emotional_arc),
        "source_notes": source_notes,
    }


def render_markdown(pack: Mapping[str, Any]) -> str:
    """Render a SongForge pack as markdown for Article/export surfaces."""
    prompt_pack = pack.get("music_prompt_pack") or {}
    parts = [
        "# SongForge Creative Pack",
        "",
        f"Safety: {pack.get('safety_note') or SAFETY_NOTE}",
        "",
        "## Themes",
        *[f"- {item}" for item in pack.get("themes") or []],
        "",
        "## Motifs",
        *[f"- {item}" for item in pack.get("motifs") or []],
        "",
        "## Source Phrases",
        *[f"- {item}" for item in pack.get("phrases") or []],
        "",
        "## Emotional Arc",
    ]
    for item in pack.get("emotional_arc") or []:
        parts.append(f"- **{item.get('label', 'Beat')}:** {item.get('summary', '')}")
    parts.extend([
        "",
        "## Lyric Draft",
        str(pack.get("lyric_draft") or "").strip(),
        "",
        "## Spoken-Word Variant",
        str(pack.get("spoken_word") or "").strip(),
        "",
        "## Music Prompt Pack",
        f"- **Mood:** {prompt_pack.get('mood', '')}",
        f"- **Tempo:** {prompt_pack.get('tempo', '')}",
        f"- **Instrumentation:** {prompt_pack.get('instrumentation', '')}",
        f"- **Vocal Direction:** {prompt_pack.get('vocal_direction', '')}",
        f"- **Structure:** {', '.join(prompt_pack.get('structure') or [])}",
        f"- **Avoid:** {', '.join(prompt_pack.get('avoid') or [])}",
        "",
        "## Source Notes",
    ])
    for note in pack.get("source_notes") or []:
        parts.append(
            f"- **{note.get('source', 'Source')}:** {note.get('excerpt', '')} "
            f"({note.get('informs', 'theme')})"
        )
    return "\n".join(parts).rstrip() + "\n"


def _themes(text: str) -> list[str]:
    tokens = _tokens(text)
    if not tokens:
        return ["creative momentum", "memory becoming form", "returning signal"]
    counts = Counter(tokens)
    return [_humanize(word) for word, _ in counts.most_common(5)][:3]


def _motifs(text: str, themes: list[str]) -> list[str]:
    bigrams = re.findall(r"\b([a-zA-Z]{4,})\s+([a-zA-Z]{4,})\b", text.lower())
    ranked = Counter(
        f"{a} {b}" for a, b in bigrams
        if a not in _STOPWORDS and b not in _STOPWORDS
    )
    motifs = [_humanize(item) for item, _ in ranked.most_common(4)]
    for theme in themes:
        if len(motifs) >= 4:
            break
        motifs.append(f"{theme} refrain")
    return motifs[:4]


def _phrases(transcript: str) -> list[str]:
    phrases = []
    for sentence in _sentences(transcript):
        if 24 <= len(sentence) <= 150:
            phrases.append(sentence)
        if len(phrases) == 5:
            break
    return phrases or ["Turn this source into a clear, original song moment."]


def _emotional_arc(transcript: str, themes: list[str]) -> list[dict[str, str]]:
    sentences = _sentences(transcript)
    if not sentences:
        sentences = [
            f"The material starts with {themes[0]}.",
            f"It turns toward {themes[1] if len(themes) > 1 else themes[0]}.",
            f"It resolves by making {themes[-1]} usable.",
        ]
    picks = [sentences[0], sentences[len(sentences) // 2], sentences[-1]]
    return [
        {"label": label, "summary": _trim(pick, 160)}
        for label, pick in zip(_ARC_LABELS, picks)
    ]


def _source_notes(
    transcript: str,
    kb_notes: list[dict[str, str]],
    themes: list[str],
) -> list[dict[str, str]]:
    notes = []
    phrase = _phrases(transcript)[0]
    if phrase:
        notes.append({
            "source": "Transcript",
            "excerpt": phrase,
            "informs": themes[0],
        })
    notes.extend(kb_notes[:3])
    return notes


def _kb_notes(knowledge_base: Mapping[str, str]) -> list[dict[str, str]]:
    notes = []
    for name, content in sorted(knowledge_base.items()):
        excerpt = _trim(next(iter(_sentences(str(content))), str(content)), 180)
        if excerpt:
            notes.append({
                "source": f"KB: {name}",
                "excerpt": excerpt,
                "informs": "voice and context",
            })
    return notes


def _lyric_draft(themes: list[str], motifs: list[str], phrases: list[str]) -> str:
    hook = themes[0]
    turn = themes[1] if len(themes) > 1 else themes[0]
    motif = motifs[0] if motifs else hook
    phrase = phrases[0].rstrip(".")
    return "\n".join([
        "[Verse 1]",
        f"We carry {hook} through the doorway light,",
        f"Turning {motif} into a signal for the night.",
        f"The room remembers: {phrase.lower()},",
        "And every loose note finds a place to land.",
        "",
        "[Chorus]",
        f"This is {hook}, this is {turn},",
        "A voice from the margins learning how to burn.",
        "No borrowed mask, no famous ghost,",
        "Just source-made thunder where it matters most.",
    ])


def _spoken_word(themes: list[str], motifs: list[str], arc: list[dict[str, str]]) -> str:
    beats = " / ".join(item["label"] for item in arc)
    motif = motifs[0] if motifs else themes[0]
    return (
        f"Begin almost whispered: {themes[0]} is not an idea, it is evidence.\n"
        f"Build through {motif}, naming the pressure without rushing it.\n"
        f"Let the arc move as {beats}.\n"
        "End direct, intimate, and original: the source is the chorus now."
    )


def _music_prompt_pack(
    themes: list[str],
    motifs: list[str],
    arc: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "mood": f"intimate, forward-moving, reflective; centered on {themes[0]}",
        "tempo": "82-96 BPM",
        "instrumentation": "warm piano or guitar pulse, restrained bass, soft percussion, subtle ambient texture",
        "vocal_direction": "clear spoken-sung delivery, close mic, conversational dynamics, no artist imitation",
        "structure": [item["label"] for item in arc] + ["Chorus", "Final refrain"],
        "avoid": [
            "living-artist imitation",
            "copyrighted lyric interpolation",
            "named soundalike references",
            "overproduced genre cliches",
        ],
    }


def _tokens(text: str) -> list[str]:
    return [
        token for token in re.findall(r"[a-zA-Z][a-zA-Z'-]{3,}", text.lower())
        if token not in _STOPWORDS
    ]


def _sentences(text: str) -> list[str]:
    return [
        _normalize(part)
        for part in re.split(r"(?<=[.!?])\s+|\n+", text)
        if _normalize(part)
    ]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _trim(text: str, limit: int) -> str:
    text = _normalize(text)
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "..."


def _humanize(value: str) -> str:
    return value.replace("_", " ").strip().lower()
