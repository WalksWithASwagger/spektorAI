"""Unified LLM content generation.

Replaces the five near-identical ``generate_*`` functions from the monolith
with one ``generate()`` that dispatches on content_type. Supports OpenAI and
Anthropic. The 'Grok' path has been removed (endpoint unverified).

Content types and their expected ``context`` dict keys:

- ``wisdom_extraction``  {'transcript'}
- ``outline_creation``   {'transcript', 'wisdom'}
- ``social_media``       {'wisdom', 'outline'}
- ``image_prompts``      {'wisdom', 'outline'}
- ``article_writing``    {'transcript', 'wisdom', 'outline'}
"""

from typing import Callable, Dict, Optional

from anthropic import Anthropic
from openai import OpenAI

from . import cache, cost
from .config import ANTHROPIC_API_KEY, DEFAULT_PROMPTS, OLLAMA_BASE_URL, OPENAI_API_KEY
from .logging import get_logger

logger = get_logger(__name__)

# Providers whose label starts with this prefix route through Ollama
# (OpenAI-compatible local inference).
OLLAMA_PROVIDER_LABEL = "Ollama (local)"

# --- Context builders per content_type -------------------------------------
# Each builder receives a dict and returns the user-message body string.

_CONTEXT_BUILDERS: Dict[str, Callable[[dict], str]] = {
    # Cleanup stage: the "user content" IS the raw transcript; the prompt
    # body tells the model what to do with it. No framing phrase added so
    # the model doesn't hallucinate one into the output.
    "transcript_cleanup": lambda ctx: ctx["transcript"],
    # Chapters stage: same shape as cleanup — raw transcript in, JSON out.
    "chapters": lambda ctx: ctx["transcript"],
    # Timestamped variant: same deal but the transcript is pre-formatted as
    # [SSSS.S] prefixed lines, one per segment.
    "chapters_timestamped": lambda ctx: ctx["transcript"],
    "wisdom_extraction": lambda ctx: (
        f"Here's the transcription to analyze:\n\n{ctx['transcript']}"
    ),
    "outline_creation": lambda ctx: (
        f"TRANSCRIPT:\n{ctx['transcript']}\n\nWISDOM:\n{ctx['wisdom']}"
    ),
    "social_media": lambda ctx: (
        f"WISDOM:\n{ctx['wisdom']}\n\nOUTLINE:\n{ctx['outline']}"
    ),
    "image_prompts": lambda ctx: (
        f"WISDOM:\n{ctx['wisdom']}\n\nOUTLINE:\n{ctx['outline']}"
    ),
    "article_writing": lambda ctx: (
        ctx.get("_user_prefix", "")
        + f"TRANSCRIPT EXCERPT:\n{ctx['transcript'][:1000]}...\n\n"
        + f"WISDOM:\n{ctx['wisdom']}\n\nOUTLINE:\n{ctx['outline']}"
    ),
    # Critique receives the draft + full source context.
    "article_critique": lambda ctx: (
        f"DRAFT ARTICLE:\n{ctx['article']}\n\n"
        f"---\nSOURCE MATERIAL\n---\n"
        f"TRANSCRIPT:\n{ctx['transcript']}\n\n"
        f"WISDOM:\n{ctx['wisdom']}\n\nOUTLINE:\n{ctx['outline']}"
    ),
    # Revise receives draft + critique + source so it can ground changes.
    # The optional ``_user_prefix`` ride-along is how the pipeline injects
    # the article-length directive without mutating the prompt template.
    "article_revise": lambda ctx: (
        ctx.get("_user_prefix", "")
        + f"DRAFT ARTICLE:\n{ctx['article']}\n\n"
        + f"---\nCRITIQUE\n---\n{ctx['critique']}\n\n"
        + f"---\nSOURCE MATERIAL\n---\n"
        + f"TRANSCRIPT:\n{ctx['transcript']}\n\n"
        + f"WISDOM:\n{ctx['wisdom']}\n\nOUTLINE:\n{ctx['outline']}"
    ),
    # Fact-check reads the article + full transcript (no summaries — need
    # direct quote-level grounding).
    "article_fact_check": lambda ctx: (
        f"ARTICLE:\n{ctx['article']}\n\n"
        f"---\nSOURCE TRANSCRIPT\n---\n{ctx['transcript']}"
    ),
}

_MAX_TOKENS: Dict[str, int] = {
    # Cleanup can return up to ~the full transcript length; give it room.
    "transcript_cleanup": 4000,
    # Chapters JSON scales with chapter count but stays modest — 2500 caps
    # at ~10 chapters with full titles/summaries.
    "chapters": 2500,
    "chapters_timestamped": 2500,
    "wisdom_extraction": 1500,
    "outline_creation": 1500,
    "social_media": 1000,
    "image_prompts": 1000,
    "article_writing": 2500,
    # Critique is a bulleted list; rarely needs more than 1500 tokens.
    "article_critique": 1500,
    # Revise returns a full article, same size budget as the initial draft.
    "article_revise": 2500,
    # Fact-check returns a JSON list of flags; small.
    "article_fact_check": 1500,
}


def _openai() -> OpenAI:
    return OpenAI(api_key=OPENAI_API_KEY)


def _anthropic() -> Anthropic:
    return Anthropic(api_key=ANTHROPIC_API_KEY)


def _ollama() -> OpenAI:
    # Ollama ignores the api_key but the SDK requires a non-empty string.
    return OpenAI(api_key="ollama", base_url=OLLAMA_BASE_URL)


def discover_ollama_models() -> Dict[str, str]:
    """Query the running Ollama daemon for installed models.

    Returns {display_name: model_id}. Empty dict if Ollama isn't reachable —
    callers should fall back to the static LLM_MODELS entry.
    """
    try:
        resp = _ollama().models.list()
    except Exception as e:
        logger.info("Ollama not reachable: %s", e)
        return {}
    out = {}
    for m in resp.data:
        # Prefer a clean display name (strip the ":latest" tag when it's there).
        mid = m.id
        label = mid.split(":")[0].replace("_", " ").title()
        out[label] = mid
    return out


def _format_prompt_body(prompt_content: str) -> str:
    """Some prompt .md files use a '## Prompt' section; pull it out if present."""
    parts = prompt_content.split("## Prompt")
    return parts[1].strip() if len(parts) > 1 else prompt_content


def _compose_kb_block(knowledge_base: Optional[Dict[str, str]]) -> str:
    """Render the user's knowledge base into a single prompt block.

    This block is STABLE across all five pipeline stages within one run —
    meaning it's the ideal prefix for Anthropic's prompt cache. Changes to
    the KB invalidate the cache; the per-stage prompt body lives separately.
    """
    if not knowledge_base:
        return ""
    kb = "\n\n".join(f"## {name}\n{content}" for name, content in knowledge_base.items())
    return (
        "Use the following knowledge base to inform your analysis and match "
        "the user's style and perspective:\n\n"
        f"{kb}\n\n"
        "When analyzing the content, please incorporate these perspectives "
        "and style guidelines."
    )


def _compose_system_prompt(prompt: str, knowledge_base: Optional[Dict[str, str]]) -> str:
    """Merge KB + per-stage prompt into a single system string (for flat
    providers like OpenAI/Ollama that don't support structured system blocks)."""
    body = _format_prompt_body(prompt)
    kb = _compose_kb_block(knowledge_base)
    if not kb:
        return body
    return f"{kb}\n\nOriginal Prompt:\n{body}"


def _call(
    provider: str,
    model: str,
    kb_block: str,
    prompt_body: str,
    user_content: str,
    max_tokens: int,
) -> str:
    if provider == "OpenAI":
        system_flat = (
            f"{kb_block}\n\nOriginal Prompt:\n{prompt_body}" if kb_block else prompt_body
        )
        response = _openai().chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_flat},
                {"role": "user", "content": user_content},
            ],
            max_tokens=max_tokens,
        )
        usage = getattr(response, "usage", None)
        if usage:
            cost.record(cost.UsageRecord(
                provider="OpenAI", model=model,
                input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            ))
        return response.choices[0].message.content or ""

    if provider == "Anthropic":
        # Split the system into two blocks: the KB (stable across stages,
        # cache_control=ephemeral) and the per-stage prompt body (varies,
        # uncached). With this split, stages 2-5 in a 5-stage pipeline run
        # read the KB from cache at 0.1x input cost.
        # https://docs.claude.com/en/docs/build-with-claude/prompt-caching
        system_blocks = []
        if kb_block:
            system_blocks.append({
                "type": "text",
                "text": kb_block,
                "cache_control": {"type": "ephemeral"},
            })
        if prompt_body:
            system_blocks.append({"type": "text", "text": prompt_body})
        response = _anthropic().messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_blocks or "",
            messages=[{"role": "user", "content": user_content}],
        )
        usage = getattr(response, "usage", None)
        if usage is not None:
            logger.info(
                "Anthropic usage: in=%s out=%s cache_read=%s cache_write=%s",
                getattr(usage, "input_tokens", "?"),
                getattr(usage, "output_tokens", "?"),
                getattr(usage, "cache_read_input_tokens", 0),
                getattr(usage, "cache_creation_input_tokens", 0),
            )
            cost.record(cost.UsageRecord(
                provider="Anthropic", model=model,
                input_tokens=getattr(usage, "input_tokens", 0) or 0,
                output_tokens=getattr(usage, "output_tokens", 0) or 0,
                cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
                cache_write_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
            ))
        return response.content[0].text

    if provider == OLLAMA_PROVIDER_LABEL:
        # Ollama speaks the OpenAI chat-completions shape with a flat string
        # system prompt. No caching, but the KB-first ordering gives us
        # prefix-caching-friendly ordering for future runtimes that support it.
        system_flat = (
            f"{kb_block}\n\nOriginal Prompt:\n{prompt_body}" if kb_block else prompt_body
        )
        response = _ollama().chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_flat},
                {"role": "user", "content": user_content},
            ],
            max_tokens=max_tokens,
        )
        # Local inference is free — record tokens for the UI breakdown but
        # with provider="Ollama (local)" which has no PRICING entry, so
        # estimate_cost() reports $0 for these.
        usage = getattr(response, "usage", None)
        if usage:
            cost.record(cost.UsageRecord(
                provider=OLLAMA_PROVIDER_LABEL, model=model,
                input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            ))
        return response.choices[0].message.content or ""
    raise ValueError(f"Unsupported provider: {provider!r}")


def generate(
    content_type: str,
    context: dict,
    provider: str,
    model: str,
    prompt: Optional[str] = None,
    knowledge_base: Optional[Dict[str, str]] = None,
    max_tokens: Optional[int] = None,
) -> Optional[str]:
    """Generate a piece of derived content.

    ``prompt`` falls back to DEFAULT_PROMPTS[content_type]. ``max_tokens``
    falls back to a sensible default per content_type. Returns None on error.

    When WHISPERFORGE_CACHE=1, the result is cached by sha256 of
    (system_prompt + user_content + provider + model + max_tokens).
    """
    if content_type not in _CONTEXT_BUILDERS:
        raise ValueError(
            f"Unknown content_type {content_type!r}. "
            f"Valid: {list(_CONTEXT_BUILDERS)}"
        )

    resolved_prompt = prompt or DEFAULT_PROMPTS.get(content_type, "")
    kb_block = _compose_kb_block(knowledge_base)
    prompt_body = _format_prompt_body(resolved_prompt)
    user_content = _CONTEXT_BUILDERS[content_type](context)
    tokens = max_tokens or _MAX_TOKENS.get(content_type, 1500)

    key = cache.make_key([
        content_type, provider, model, str(tokens),
        cache.text_hash(kb_block),
        cache.text_hash(prompt_body),
        cache.text_hash(user_content),
    ])

    def _compute() -> Optional[str]:
        try:
            return _call(provider, model, kb_block, prompt_body, user_content, tokens)
        except Exception as e:
            logger.error("generate(%s) failed on %s %s: %s", content_type, provider, model, e)
            return None

    return cache.cached_or_compute(key, _compute)


# --- Ad-hoc helpers that don't fit the generate() contract -----------------

def apply_prompt(
    text: str,
    prompt: str,
    provider: str,
    model: str,
    knowledge_base: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    """Generic 'analyze this text with this prompt' helper used by legacy callers."""
    kb_block = _compose_kb_block(knowledge_base)
    prompt_body = _format_prompt_body(prompt)
    user_content = f"Here's the transcription to analyze:\n\n{text}"
    try:
        return _call(provider, model, kb_block, prompt_body, user_content, max_tokens=1500)
    except Exception as e:
        logger.error("apply_prompt failed on %s %s: %s", provider, model, e)
        return None


# --- Structured helpers (title / summary / tags) ---------------------------
# All three use OpenAI's JSON-schema-enforced "Structured Outputs" so we never
# have to regex-parse prose. The schema is the contract. gpt-4o-mini is the
# cheap tier for this kind of bounded extraction work.

_STRUCTURED_MODEL = "gpt-4o-mini"


def _structured_call(schema_name: str, schema: dict, system: str, user: str, max_tokens: int = 200) -> Optional[dict]:
    """Call OpenAI with a strict JSON schema; return the parsed dict or None."""
    import json as _json
    try:
        response = _openai().chat.completions.create(
            model=_STRUCTURED_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            temperature=0.3,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                },
            },
        )
        usage = getattr(response, "usage", None)
        if usage:
            cost.record(cost.UsageRecord(
                provider="OpenAI", model=_STRUCTURED_MODEL,
                input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            ))
        raw = response.choices[0].message.content or "{}"
        return _json.loads(raw)
    except Exception as e:
        logger.warning("structured call %s failed: %s", schema_name, e)
        return None


def generate_title(transcript: str) -> str:
    """Produce a 5-7 word descriptive title. Schema-enforced JSON output."""
    result = _structured_call(
        schema_name="title",
        schema={
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "A clear, descriptive 5-7 word title capturing the main topic.",
                }
            },
            "required": ["title"],
            "additionalProperties": False,
        },
        system="You create concise, descriptive titles that capture the essence of content.",
        user=f"Generate a 5-7 word title for this transcript:\n\n{transcript[:2000]}",
        max_tokens=60,
    )
    return (result or {}).get("title", "").strip() or "Audio Transcription"


def generate_summary(transcript: str) -> str:
    """Single-sentence summary. Schema-enforced JSON output."""
    result = _structured_call(
        schema_name="summary",
        schema={
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "A single insightful sentence summarizing the key message.",
                }
            },
            "required": ["summary"],
            "additionalProperties": False,
        },
        system="You distill content into one sharp, insightful sentence.",
        user=f"Summarize this transcript in one sentence:\n\n{transcript[:2000]}",
        max_tokens=120,
    )
    return (result or {}).get("summary", "").strip() or "Summary of audio content"


def _format_timestamped_transcript(segments: list) -> str:
    """Render ``[{start, end, text, speaker?}]`` as ``[SSSS.S] text`` lines
    suitable for the ``chapters_timestamped`` prompt."""
    lines = []
    for s in segments:
        start = float(s.get("start", 0.0))
        text_ = (s.get("text") or "").strip()
        if not text_:
            continue
        spk = s.get("speaker")
        prefix = f"[{start:.1f}]" + (f" {spk}:" if spk else "")
        lines.append(f"{prefix} {text_}")
    return "\n".join(lines)


def generate_chapters(
    transcript: str,
    provider: str = "Anthropic",
    model: str = "claude-haiku-4-5",
    knowledge_base: Optional[Dict[str, str]] = None,
    segments: Optional[list] = None,
) -> list[dict]:
    """Segment a transcript into topical chapters.

    Returns a list of ``{"title", "summary", "start_quote", "start_seconds"?}``
    dicts — empty on failure or if the model returned unparseable output. Uses
    the generate() machinery so it benefits from caching + the active provider.

    When ``segments`` is provided (shape: the list from
    ``audio.TranscriptionDetails.segments``), the transcript is reformatted
    with per-segment ``[SSSS.S]`` prefixes and the timestamp-aware prompt
    variant is used. The model then picks ``start_seconds`` per chapter, which
    flows through to Notion's ``[M:SS]`` / ``[H:MM:SS]`` rendering.
    """
    if segments:
        input_text = _format_timestamped_transcript(segments)
        content_type = "chapters_timestamped"
    else:
        input_text = transcript
        content_type = "chapters"

    raw = generate(
        content_type,
        {"transcript": input_text},
        provider,
        model,
        # Chapters are a structural extraction task — skip the KB so the model
        # doesn't try to inject style commentary into the titles.
        knowledge_base=None,
    )
    if not raw:
        return []

    # Defensive JSON parse: strip markdown fences if the model added them,
    # then look for the outermost {...} block. Anthropic usually returns
    # clean JSON when told to; OpenAI sometimes wraps it.
    import json as _json
    text = raw.strip()
    if text.startswith("```"):
        # Drop the first and last fence lines
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]) if len(lines) >= 3 else text

    # Find the outermost JSON object
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        logger.warning("generate_chapters: no JSON object found in output")
        return []
    try:
        data = _json.loads(text[start : end + 1])
    except _json.JSONDecodeError as e:
        logger.warning("generate_chapters: JSON parse failed: %s", e)
        return []

    chapters = data.get("chapters", [])

    def _coerce(c: dict) -> dict:
        out = {
            "title": str(c.get("title", "")).strip(),
            "summary": str(c.get("summary", "")).strip(),
            "start_quote": str(c.get("start_quote", "")).strip(),
        }
        ts = c.get("start_seconds")
        if isinstance(ts, (int, float)):
            out["start_seconds"] = float(ts)
        return out

    return [_coerce(c) for c in chapters if isinstance(c, dict) and c.get("title")]


def generate_tags(content: str, max_tags: int = 6) -> list[str]:
    """Up to ``max_tags`` short content tags. Schema-enforced JSON array."""
    result = _structured_call(
        schema_name="content_tags",
        schema={
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": f"Up to {max_tags} short (1-2 word) tags, lowercase, no hashes.",
                    "minItems": 1,
                    "maxItems": max_tags,
                }
            },
            "required": ["tags"],
            "additionalProperties": False,
        },
        system=f"You generate up to {max_tags} short (1-2 word) content tags. Lowercase. No hashes. No duplicates.",
        user=content[:2000],
        max_tokens=120,
    )
    tags = (result or {}).get("tags", [])
    # Defensive: ensure strings + strip any stray hashes/whitespace.
    return [str(t).strip(" #").lower() for t in tags if t][:max_tags]
