"""Full content-generation pipeline.

Runs the five-stage pipeline (wisdom → outline → social → image prompts →
article) over either a transcript (audio path) or pasted text. UI layers get
progress via an optional callback instead of hardcoded Streamlit progress bars.
"""

from dataclasses import dataclass
from typing import Callable, Dict, Optional

from . import images, llm
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
    # Topical segmentation with {title, summary, start_quote} per chapter.
    # Empty when chapters=False or the model couldn't produce valid JSON.
    chapters: list = None  # type: ignore[assignment]
    # Agentic drafting intermediates — populated when agentic=True.
    article_draft: Optional[str] = None        # pre-critique version
    article_critique: Optional[str] = None     # the critique bullets
    # Fact-check flags — populated when fact_check=True. Shape:
    # [{"claim": str, "issue": str}]. Empty list means clean.
    fact_check_flags: list = None  # type: ignore[assignment]
    # Generated images (populated when generate_images=True). Shape:
    # [{"path": str, "prompt": str, "succeeded": bool, "error": Optional[str]}]
    generated_images: list = None  # type: ignore[assignment]
    # Alternate-provider comparison article (populated when
    # compare_provider + compare_model are set). Rendered as a second
    # card in the Output so you can A/B voices without a fresh run.
    article_compare: Optional[str] = None
    compare_label: Optional[str] = None   # e.g. "OpenAI gpt-4o"

    def __post_init__(self):
        if self.chapters is None:
            self.chapters = []
        if self.fact_check_flags is None:
            self.fact_check_flags = []
        if self.generated_images is None:
            self.generated_images = []


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
    chapters: bool = True,
    segments: Optional[list] = None,
    agentic: bool = False,
    fact_check: bool = False,
    generate_images: bool = False,
    image_style: Optional[str] = None,
    image_aspect_ratio: str = "16:9",
    image_model: str = "gemini-2.5-flash-image",
    image_output_dir: Optional[str] = None,
    article_length_words: int = 1500,
    user: Optional[str] = None,
    rag_mode: str = "auto",
    compare_provider: Optional[str] = None,
    compare_model: Optional[str] = None,
) -> PipelineResult:
    """Execute the content pipeline.

    When ``cleanup`` is True (default), a stage-0 pass strips filler words,
    false starts, and ASR typos from the transcript before downstream stages
    see it. The cleaned text is used for all subsequent stages; the original
    is preserved on ``PipelineResult.raw_transcript``.

    When ``chapters`` is True (default), a short post-cleanup pass segments
    the transcript into {title, summary, start_quote} chapters. Useful for
    long-form content where readers want to skim; cheap (single Haiku call).

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

    # Stage 0.5: chapters — structural segmentation. Runs before the voice
    # stages because later stages might re-phrase things in ways that drift
    # from the transcript's literal topic boundaries. When ``segments`` is
    # provided (e.g. WhisperX backend populated them), the timestamped variant
    # runs and each chapter gets a ``start_seconds`` for Notion jump-links.
    if chapters:
        _report(0.05, "Chaptering...")
        result.chapters = llm.generate_chapters(
            transcript, provider, model, segments=segments,
        )
        _report(0.1, "Chaptering...")

    # Stage 1: wisdom (needs transcript)
    _report(0.1, _STAGES[0][1])
    result.wisdom = llm.generate(
        "wisdom_extraction",
        {"transcript": transcript},
        provider,
        model,
        prompt=prompts.get("wisdom_extraction"),
        knowledge_base=knowledge_base,
            user=user,
            rag_mode=rag_mode,
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
            user=user,
            rag_mode=rag_mode,
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
            user=user,
            rag_mode=rag_mode,
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
            user=user,
            rag_mode=rag_mode,
    )
    _report(0.8, _STAGES[3][1])

    # Stage 5: article draft (always runs — first pass of the agentic flow).
    # Length budget: ~1.4 tokens/word + 30% headroom for headings/structure.
    article_max_tokens = max(800, int(article_length_words * 1.8))
    article_user_prefix = (
        f"Target length: approximately {article_length_words} words. "
        f"Adjust depth and section count to fit, but never pad with filler.\n\n"
    )
    _report(0.8, _STAGES[4][1])
    draft = llm.generate(
        "article_writing",
        {
            "transcript": transcript,
            "wisdom": result.wisdom or "",
            "outline": result.outline or "",
            "_user_prefix": article_user_prefix,   # consumed by context builder if present
        },
        provider,
        model,
        prompt=prompts.get("article_writing"),
        knowledge_base=knowledge_base,
            user=user,
            rag_mode=rag_mode,
        max_tokens=article_max_tokens,
    )
    result.article = draft
    result.article_draft = draft

    # Stage 6-7: agentic critique + revise. Opt-in via agentic=True.
    # Gets cheap ($~0.005 on Haiku 4.5 + prompt caching) but markedly
    # improves long-form quality — the critique pass catches voice drift
    # and filler that single-shot drafting misses.
    if agentic and draft:
        _report(0.85, "Critiquing draft...")
        critique = llm.generate(
            "article_critique",
            {
                "article": draft,
                "transcript": transcript,
                "wisdom": result.wisdom or "",
                "outline": result.outline or "",
            },
            provider,
            model,
            prompt=prompts.get("article_critique"),
            knowledge_base=knowledge_base,
            user=user,
            rag_mode=rag_mode,
        )
        result.article_critique = critique
        _report(0.9, "Revising...")
        if critique:
            revised = llm.generate(
                "article_revise",
                {
                    "article": draft,
                    "critique": critique,
                    "transcript": transcript,
                    "wisdom": result.wisdom or "",
                    "outline": result.outline or "",
                    "_user_prefix": article_user_prefix,
                },
                provider,
                model,
                prompt=prompts.get("article_revise"),
                knowledge_base=knowledge_base,
            user=user,
            rag_mode=rag_mode,
                max_tokens=article_max_tokens,
            )
            if revised:
                result.article = revised

    # Stage 7.25: optional A/B comparison — run article_writing once more
    # with an alternate provider/model on the same context. Useful for
    # deciding whether to promote a draft (Haiku → Sonnet, say) without
    # a full fresh pipeline run.
    if compare_provider and compare_model and result.article:
        _report(0.93, "Generating comparison article...")
        try:
            compare = llm.generate(
                "article_writing",
                {
                    "transcript": transcript,
                    "wisdom": result.wisdom or "",
                    "outline": result.outline or "",
                    "_user_prefix": article_user_prefix,
                },
                compare_provider,
                compare_model,
                prompt=prompts.get("article_writing"),
                knowledge_base=knowledge_base,
                max_tokens=article_max_tokens,
                user=user,
                rag_mode=rag_mode,
            )
            if compare:
                result.article_compare = compare
                result.compare_label = f"{compare_provider} {compare_model}"
        except Exception as e:
            logger.warning("comparison article failed: %s", e)

    # Stage 7.5: optional image generation. Parses the image_prompts output
    # into distinct prompts and generates one PNG per prompt via nano-banana.
    # Sits after the article stage (even under agentic mode) so the critique
    # can inform the prompts if Kris ever wires that feedback loop; today
    # it just consumes whatever image_prompts stage 4 emitted.
    if generate_images and result.image_prompts:
        _report(0.92, "Generating images...")
        try:
            prompts_list = images.extract_prompts(result.image_prompts)
            if prompts_list:
                out_dir = (
                    images.run_output_dir()
                    if not image_output_dir else
                    images.Path(image_output_dir)
                )
                image_results = images.generate_images(
                    prompts_list,
                    out_dir,
                    model=image_model,
                    aspect_ratio=image_aspect_ratio,
                    style=image_style,
                )
                result.generated_images = [
                    {
                        "path": str(r.output_path),
                        "prompt": r.prompt,
                        "succeeded": r.succeeded,
                        "error": r.error,
                    }
                    for r in image_results
                ]
        except Exception as e:
            logger.warning("image generation failed: %s", e)

    # Stage 8: optional fact-check pass. Runs against whichever article is
    # current (revised if agentic ran, draft otherwise). Output is
    # structured JSON so the UI can render a clear flag list.
    if fact_check and result.article:
        _report(0.95, "Fact-checking...")
        raw = llm.generate(
            "article_fact_check",
            {"article": result.article, "transcript": transcript},
            provider,
            model,
            prompt=prompts.get("article_fact_check"),
            knowledge_base=None,  # fact-check is grounded, not stylistic
        )
        result.fact_check_flags = _parse_fact_check(raw)

    _report(1.0, "Done")

    return result


def _parse_fact_check(raw: Optional[str]) -> list:
    """Defensive JSON parse of the fact-check output. Returns the ``flags``
    list or ``[]`` on any failure — we don't want a bad critique call to
    sink the whole pipeline result."""
    if not raw:
        return []
    import json as _json
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]) if len(lines) >= 3 else text
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return []
    try:
        data = _json.loads(text[start : end + 1])
    except _json.JSONDecodeError:
        return []
    flags = data.get("flags", [])
    return [
        {"claim": str(f.get("claim", "")).strip(), "issue": str(f.get("issue", "")).strip()}
        for f in flags
        if isinstance(f, dict) and f.get("claim")
    ]
