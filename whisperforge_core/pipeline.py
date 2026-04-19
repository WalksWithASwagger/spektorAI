"""Full content-generation pipeline.

Runs the five-stage pipeline (wisdom → outline → social → image prompts →
article) over either a transcript (audio path) or pasted text. UI layers get
progress via an optional callback instead of hardcoded Streamlit progress bars.
"""

from dataclasses import dataclass
from typing import Callable, Dict, Optional

from . import llm
from .logging import get_logger

logger = get_logger(__name__)

ProgressCallback = Callable[[float, str], None]  # (fraction_0_to_1, label) -> None


@dataclass
class PipelineResult:
    wisdom: Optional[str] = None
    outline: Optional[str] = None
    social_posts: Optional[str] = None
    image_prompts: Optional[str] = None
    article: Optional[str] = None
    # Raw transcript as returned from ASR. Populated when cleanup is enabled
    # so callers can still see what the transcriber actually heard.
    raw_transcript: Optional[str] = None
    cleaned_transcript: Optional[str] = None


_STAGES = [
    ("wisdom_extraction", "Extracting wisdom...", "wisdom"),
    ("outline_creation", "Creating outline...", "outline"),
    ("social_media", "Generating social media...", "social_posts"),
    ("image_prompts", "Creating image prompts...", "image_prompts"),
    ("article_writing", "Writing full article...", "article"),
]


def run(
    transcript: str,
    provider: str,
    model: str,
    prompts: Optional[Dict[str, str]] = None,
    knowledge_base: Optional[Dict[str, str]] = None,
    progress: Optional[ProgressCallback] = None,
    cleanup: bool = True,
) -> PipelineResult:
    """Execute the content pipeline.

    When ``cleanup`` is True (default), a stage-0 pass strips filler words,
    false starts, and ASR typos from the transcript before downstream stages
    see it. Disabled for raw/unaltered runs or when the transcript is already
    clean (e.g. pasted text). The cleaned text is used for all subsequent
    stages; the original is preserved on ``PipelineResult.raw_transcript``.

    ``prompts`` is an optional {content_type: template} override dict (typically
    the user's custom prompts loaded via whisperforge_core.prompts). Missing
    keys fall back to DEFAULT_PROMPTS inside llm.generate().
    """
    prompts = prompts or {}
    result = PipelineResult(raw_transcript=transcript)

    def _report(frac: float, label: str) -> None:
        if progress:
            progress(frac, label)

    # Stage 0: optional transcript cleanup. ~5% budget. Failure falls back to
    # the raw transcript rather than aborting the whole run.
    if cleanup:
        _report(0.0, "Cleaning transcript...")
        cleaned = llm.generate(
            "transcript_cleanup",
            {"transcript": transcript},
            provider,
            model,
            prompt=prompts.get("transcript_cleanup"),
            # Cleanup doesn't need the KB — it's mechanical editing,
            # not stylistic generation. Skipping the KB here also keeps
            # this call fast and leaves cache-prefix room for stages 1-5.
            knowledge_base=None,
        )
        if cleaned:
            transcript = cleaned
            result.cleaned_transcript = cleaned
        _report(0.05, "Cleaning transcript...")

    # Stage 1: wisdom (needs transcript)
    _report(0.05, _STAGES[0][1])
    result.wisdom = llm.generate(
        "wisdom_extraction",
        {"transcript": transcript},
        provider,
        model,
        prompt=prompts.get("wisdom_extraction"),
        knowledge_base=knowledge_base,
    )
    _report(0.2, _STAGES[0][1])

    # Stage 2: outline (needs transcript + wisdom)
    _report(0.2, _STAGES[1][1])
    result.outline = llm.generate(
        "outline_creation",
        {"transcript": transcript, "wisdom": result.wisdom or ""},
        provider,
        model,
        prompt=prompts.get("outline_creation"),
        knowledge_base=knowledge_base,
    )
    _report(0.4, _STAGES[1][1])

    # Stage 3: social (needs wisdom + outline)
    _report(0.4, _STAGES[2][1])
    result.social_posts = llm.generate(
        "social_media",
        {"wisdom": result.wisdom or "", "outline": result.outline or ""},
        provider,
        model,
        prompt=prompts.get("social_media"),
        knowledge_base=knowledge_base,
    )
    _report(0.6, _STAGES[2][1])

    # Stage 4: image prompts
    _report(0.6, _STAGES[3][1])
    result.image_prompts = llm.generate(
        "image_prompts",
        {"wisdom": result.wisdom or "", "outline": result.outline or ""},
        provider,
        model,
        prompt=prompts.get("image_prompts"),
        knowledge_base=knowledge_base,
    )
    _report(0.8, _STAGES[3][1])

    # Stage 5: article
    _report(0.8, _STAGES[4][1])
    result.article = llm.generate(
        "article_writing",
        {
            "transcript": transcript,
            "wisdom": result.wisdom or "",
            "outline": result.outline or "",
        },
        provider,
        model,
        prompt=prompts.get("article_writing"),
        knowledge_base=knowledge_base,
    )
    _report(1.0, "Done")

    return result
