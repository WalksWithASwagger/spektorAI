"""Image generation via Google Nano Banana (Gemini 2.5 Flash Image).

Borrowed and trimmed from ``kk-ai-ecosystem/tools/image-gen/generate.py`` —
just the core generation function, style registry, and aspect-ratio presets.
The original tool has a CLI + image-prompts.md batch parser; we don't need
those because WhisperForge already produces structured image prompts as a
pipeline stage.

Requires:
  - ``google-genai`` package (``pip install google-genai``)
  - ``GOOGLE_API_KEY`` env var (get one at https://aistudio.google.com/app/apikey)
  - ``pyyaml`` for the style registry

Callable surface:
  - ``generate_image(prompt, output_path, ...)`` — single image
  - ``generate_images(prompts, output_dir, ...)`` — batch
  - ``list_styles()``, ``get_style_suffix()`` — style registry access

Cost semantics are exposed through ``whisperforge_core.cost`` just like LLM
calls — nano-banana charges per image, not per token, so we record one
``UsageRecord`` per successful generation with ``audio_seconds=1.0`` as a
proxy budget slot. Pricing is under ``PRICING[("Google", model)]``.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from . import cost
from .config import CACHE_DIR, PROJECT_ROOT
from .logging import get_logger

logger = get_logger(__name__)

# --- Style registry --------------------------------------------------------

_STYLES_PATH = PROJECT_ROOT / "styles" / "image_styles.yaml"
_DEFAULT_MODEL = "gemini-2.5-flash-image"

ASPECT_RATIOS: dict[str, str] = {
    "square": "1:1",
    "landscape": "16:9",
    "portrait": "9:16",
    "linkedin": "16:9",
    "instagram": "1:1",
    "twitter": "16:9",
    "story": "9:16",
}


def _load_styles_file() -> dict:
    """Read the YAML style registry. Empty dict if missing."""
    if not _STYLES_PATH.exists():
        return {}
    try:
        import yaml  # lazy — PyYAML is only needed on the image path
        with open(_STYLES_PATH) as f:
            return (yaml.safe_load(f) or {}).get("styles", {})
    except Exception as e:
        logger.warning("failed to load image styles: %s", e)
        return {}


def list_styles() -> dict:
    """All registered styles keyed by id. Each value has ``name``,
    ``description``, ``suffix``, and optionally ``default``."""
    return _load_styles_file()


def default_style() -> str:
    """Return the id of the default style, or ``'kk'`` if none marked."""
    for sid, cfg in _load_styles_file().items():
        if cfg.get("default"):
            return sid
    return "kk"


def get_style_suffix(style_id: str) -> str:
    """Return the prompt-suffix string for a style, or empty."""
    cfg = _load_styles_file().get(style_id, {})
    return cfg.get("suffix", "") or ""


# --- Core generation -------------------------------------------------------

@dataclass
class ImageResult:
    """One image generation outcome."""
    output_path: Path
    prompt: str
    model: str
    aspect_ratio: str
    style: Optional[str] = None
    succeeded: bool = True
    error: Optional[str] = None


def _genai_client():
    """Build a Gemini client. Imported lazily so non-image flows don't pay
    the import cost."""
    from google import genai
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY not set. Get one at https://aistudio.google.com/app/apikey "
            "and add to .env."
        )
    return genai.Client(api_key=api_key)


def generate_image(
    prompt: str,
    output_path: str | Path,
    *,
    model: str = _DEFAULT_MODEL,
    aspect_ratio: str = "16:9",
    style: Optional[str] = None,
    reference_image: Optional[str | Path] = None,
) -> ImageResult:
    """Generate a single image with Gemini image models.

    Keys from Kris's original tool:
      - ``style`` resolves via the YAML registry; pass ``"none"`` to skip
        the style suffix entirely.
      - ``aspect_ratio`` accepts either a preset name ("linkedin", "square",
        …) or a raw Gemini ratio string ("16:9", "1:1", "9:16").
      - ``reference_image`` is treated as a style reference (look-and-feel
        only, not a text/content source). The "mockup" mode from the
        original tool isn't exposed here — WhisperForge doesn't need it.

    Returns an ``ImageResult``; never raises for API-layer problems so a
    batch run doesn't abort on a single failed image.
    """
    from google.genai import types
    from PIL import Image as PILImage

    output_path = Path(output_path)

    # Resolve aspect ratio preset → Gemini ratio string
    ratio = ASPECT_RATIOS.get(aspect_ratio, aspect_ratio)

    # Apply style suffix unless style is explicitly "none" or missing
    full_prompt = prompt
    if style is None:
        style = default_style()
    if style and style != "none":
        suffix = get_style_suffix(style)
        if suffix:
            full_prompt = f"{prompt}\n\n{suffix}"

    try:
        client = _genai_client()
    except RuntimeError as e:
        logger.error("image generation skipped: %s", e)
        return ImageResult(
            output_path=output_path, prompt=prompt, model=model,
            aspect_ratio=ratio, style=style, succeeded=False, error=str(e),
        )

    config = types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        image_config=types.ImageConfig(aspect_ratio=ratio),
    )

    # Build contents: optional reference image first, then prompt.
    contents: list = []
    if reference_image:
        ref_path = Path(reference_image)
        if not ref_path.exists():
            logger.warning("reference image missing: %s", reference_image)
        else:
            try:
                contents.append(PILImage.open(ref_path))
                full_prompt = (
                    "IMPORTANT: Use the provided image ONLY as a visual style "
                    "reference (textures, grain, color palette, layout energy). "
                    "Do NOT copy any text, words, brand names, or written "
                    "content from the reference image. The actual text and "
                    "content MUST come from the prompt below.\n\n"
                    f"{full_prompt}"
                )
            except Exception as e:
                logger.warning("failed to load reference image %s: %s", ref_path, e)

    contents.append(full_prompt)

    try:
        response = client.models.generate_content(
            model=model, contents=contents, config=config,
        )
    except Exception as e:
        logger.error("Gemini generate_content failed: %s", e)
        return ImageResult(
            output_path=output_path, prompt=prompt, model=model,
            aspect_ratio=ratio, style=style, succeeded=False, error=str(e),
        )

    # Locate the image bytes in the response parts
    for part in getattr(response, "parts", []):
        if getattr(part, "inline_data", None) is not None:
            try:
                image = part.as_image()
                output_path.parent.mkdir(parents=True, exist_ok=True)
                image.save(output_path)
                # Record one successful generation for cost tracking.
                cost.record(cost.UsageRecord(
                    provider="Google", model=model,
                    input_tokens=0, output_tokens=0,
                    # ASR billing slot; per-image pricing is added to the
                    # PRICING table as ASR_PRICING_PER_MINUTE style.
                    audio_seconds=60.0,  # billed as one minute = one image
                ))
                return ImageResult(
                    output_path=output_path, prompt=prompt, model=model,
                    aspect_ratio=ratio, style=style, succeeded=True,
                )
            except Exception as e:
                logger.error("failed to save image: %s", e)
                return ImageResult(
                    output_path=output_path, prompt=prompt, model=model,
                    aspect_ratio=ratio, style=style, succeeded=False,
                    error=str(e),
                )

    # No image in the response — usually a safety block or empty completion.
    text = getattr(response, "text", "")
    msg = f"no image in response{'; text: ' + text[:200] if text else ''}"
    logger.warning(msg)
    return ImageResult(
        output_path=output_path, prompt=prompt, model=model,
        aspect_ratio=ratio, style=style, succeeded=False, error=msg,
    )


# --- Parsing image_prompts output -----------------------------------------

def extract_prompts(image_prompts_text: str) -> list[str]:
    """Pull distinct prompt strings out of the ``image_prompts`` stage output.

    Models produce one of several markdown shapes. This tries each format
    in descending order of reliability, stopping at the first one that
    yields more than one distinct prompt. If nothing structured is found,
    returns the whole text as a single prompt so the user at least gets
    one image.
    """
    if not image_prompts_text or not image_prompts_text.strip():
        return []

    text = image_prompts_text.strip()

    # Strategy 1: "N. **Label**: prompt text" — current default prompt format.
    # Label is optional; just the numbered "N. prompt" also matches.
    pattern = re.compile(
        r"^\s*(\d+)\.\s+(?:\*\*[^*]+\*\*\s*[:—-]\s*)?(.+?)(?=^\s*\d+\.\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    matches = pattern.findall(text)
    if len(matches) >= 2:
        return [m[1].strip().rstrip("-").strip() for m in matches if m[1].strip()]

    # Strategy 2: markdown blockquotes after **Prompt:** labels (Kris's
    # `image-prompts.md` format used by the nano-banana tool)
    blocks = re.findall(
        r"\*\*Prompt:\*\*\s*\n((?:>[^\n]*(?:\n|$))+)",
        text, flags=re.MULTILINE,
    )
    if blocks:
        out = []
        for block in blocks:
            lines = []
            for line in block.splitlines():
                if line.startswith(">"):
                    lines.append(line[1:].lstrip())
            if lines:
                out.append("\n".join(lines).strip())
        if out:
            return out

    # Strategy 3: numbered markdown headings (## 1. Title / ### 1. Title)
    sections = re.split(r"^#{1,3}\s*\d+\.\s*", text, flags=re.MULTILINE)[1:]
    if len(sections) >= 2:
        return [s.strip().split("\n\n", 1)[0].strip() for s in sections if s.strip()]

    # Strategy 4 (last-resort): treat the whole text as one prompt. This
    # happens when the model ignored the format directive and wrote a
    # narrative instead — better to produce one image than zero.
    return [text]


def generate_images(
    prompts: List[str],
    output_dir: str | Path,
    *,
    model: str = _DEFAULT_MODEL,
    aspect_ratio: str = "16:9",
    style: Optional[str] = None,
    reference_image: Optional[str | Path] = None,
) -> List[ImageResult]:
    """Generate an image for each prompt. Filenames are numbered + slugged
    from the prompt's first few words so a run's images are easy to pair
    back to their prompts visually.
    """
    output_dir = Path(output_dir)
    results: List[ImageResult] = []
    for i, prompt in enumerate(prompts, 1):
        # Build a short stable filename from the prompt's opening
        lead = re.sub(r"[^a-z0-9]+", "-", prompt.lower()[:60]).strip("-") or "image"
        digest = hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:6]
        out = output_dir / f"{i:02d}-{lead}-{digest}.png"
        result = generate_image(
            prompt, out, model=model, aspect_ratio=aspect_ratio,
            style=style, reference_image=reference_image,
        )
        results.append(result)
    return results


def run_output_dir(run_id: Optional[str] = None) -> Path:
    """Per-run output directory under CACHE_DIR/images/. Defaults to a
    timestamp-based id so successive runs don't stomp on each other."""
    from datetime import datetime
    run_id = run_id or datetime.now().strftime("%Y%m%d-%H%M%S")
    out = CACHE_DIR / "images" / run_id
    out.mkdir(parents=True, exist_ok=True)
    return out
