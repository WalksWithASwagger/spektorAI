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

from . import cache
from .config import ANTHROPIC_API_KEY, DEFAULT_PROMPTS, OPENAI_API_KEY
from .logging import get_logger

logger = get_logger(__name__)

# --- Context builders per content_type -------------------------------------
# Each builder receives a dict and returns the user-message body string.

_CONTEXT_BUILDERS: Dict[str, Callable[[dict], str]] = {
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
        f"TRANSCRIPT EXCERPT:\n{ctx['transcript'][:1000]}...\n\n"
        f"WISDOM:\n{ctx['wisdom']}\n\nOUTLINE:\n{ctx['outline']}"
    ),
}

_MAX_TOKENS: Dict[str, int] = {
    "wisdom_extraction": 1500,
    "outline_creation": 1500,
    "social_media": 1000,
    "image_prompts": 1000,
    "article_writing": 2500,
}


def _openai() -> OpenAI:
    return OpenAI(api_key=OPENAI_API_KEY)


def _anthropic() -> Anthropic:
    return Anthropic(api_key=ANTHROPIC_API_KEY)


def _format_prompt_body(prompt_content: str) -> str:
    """Some prompt .md files use a '## Prompt' section; pull it out if present."""
    parts = prompt_content.split("## Prompt")
    return parts[1].strip() if len(parts) > 1 else prompt_content


def _compose_system_prompt(prompt: str, knowledge_base: Optional[Dict[str, str]]) -> str:
    body = _format_prompt_body(prompt)
    if not knowledge_base:
        return body
    kb = "\n\n".join(f"## {name}\n{content}" for name, content in knowledge_base.items())
    return (
        "Use the following knowledge base to inform your analysis and match "
        "the user's style and perspective:\n\n"
        f"{kb}\n\n"
        "When analyzing the content, please incorporate these perspectives "
        "and style guidelines.\n\n"
        f"Original Prompt:\n{body}"
    )


def _call(
    provider: str,
    model: str,
    system_prompt: str,
    user_content: str,
    max_tokens: int,
) -> str:
    if provider == "OpenAI":
        response = _openai().chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""
    if provider == "Anthropic":
        response = _anthropic().messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
        return response.content[0].text
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
    system = _compose_system_prompt(resolved_prompt, knowledge_base)
    user_content = _CONTEXT_BUILDERS[content_type](context)
    tokens = max_tokens or _MAX_TOKENS.get(content_type, 1500)

    key = cache.make_key([
        content_type, provider, model, str(tokens),
        cache.text_hash(system), cache.text_hash(user_content),
    ])

    def _compute() -> Optional[str]:
        try:
            return _call(provider, model, system, user_content, tokens)
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
    system = _compose_system_prompt(prompt, knowledge_base)
    user_content = f"Here's the transcription to analyze:\n\n{text}"
    try:
        return _call(provider, model, system, user_content, max_tokens=1500)
    except Exception as e:
        logger.error("apply_prompt failed on %s %s: %s", provider, model, e)
        return None


def generate_title(transcript: str) -> str:
    """Produce a 5-7 word descriptive title via gpt-3.5-turbo."""
    try:
        response = _openai().chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that creates concise, descriptive titles.",
                },
                {
                    "role": "user",
                    "content": (
                        "Create a clear, descriptive title (5-7 words) that captures "
                        f"the main topic of this transcript:\nTranscript: {transcript[:1000]}...\n\n"
                        "Return only the title, no quotes or additional text."
                    ),
                },
            ],
            max_tokens=50,
            temperature=0.3,
        )
        return (response.choices[0].message.content or "").strip() or "Audio Transcription"
    except Exception as e:
        logger.warning("generate_title failed: %s", e)
        return "Audio Transcription"


def generate_summary(transcript: str) -> str:
    """One-sentence summary via gpt-3.5-turbo."""
    try:
        response = _openai().chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that creates concise, insightful summaries.",
                },
                {
                    "role": "user",
                    "content": (
                        "Create a single, insightful sentence that summarizes the key "
                        f"message or main insight from this transcript:\n"
                        f"Transcript: {transcript[:1000]}...\n\n"
                        "Return only the summary sentence, no additional text."
                    ),
                },
            ],
            max_tokens=100,
            temperature=0.3,
        )
        return (response.choices[0].message.content or "").strip() or "Summary of audio content"
    except Exception as e:
        logger.warning("generate_summary failed: %s", e)
        return "Summary of audio content"


def generate_tags(content: str, max_tags: int = 6) -> list[str]:
    """Return up to ``max_tags`` short content tags."""
    try:
        response = _openai().chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Generate up to {max_tags} short (1-2 word) content tags, "
                        "comma-separated, no hashes, no quotes."
                    ),
                },
                {"role": "user", "content": content[:2000]},
            ],
            max_tokens=100,
            temperature=0.3,
        )
        raw = response.choices[0].message.content or ""
        return [t.strip(" #") for t in raw.split(",") if t.strip()][:max_tags]
    except Exception as e:
        logger.warning("generate_tags failed: %s", e)
        return []
