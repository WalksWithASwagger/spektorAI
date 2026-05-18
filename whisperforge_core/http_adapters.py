"""HTTP clients that let the Streamlit frontend talk to the microservices.

Selected by DEPLOY_MODE=services (see config + adapters.py). Each adapter wraps
a single microservice endpoint with the X-API-Key: SERVICE_TOKEN contract.

Kept separate from adapters.py because these imports (requests) are only
needed in the frontend container, not in the monolith path.
"""

import tempfile
from pathlib import Path
from typing import Callable, Dict, Optional

import requests

from . import notion as notion_mod
from . import pipeline as pipeline_mod
from .config import PROCESSING_URL, SERVICE_TOKEN, STORAGE_URL, TRANSCRIPTION_URL
from .logging import get_logger

logger = get_logger("http_adapters")

_HEADERS = {"X-API-Key": SERVICE_TOKEN or ""}
_TIMEOUT = 600  # seconds — big files + LLM calls take a while


class HttpTranscriber:
    def transcribe(self, source, suffix: str = ".mp3", progress=None) -> str:
        # Accepts path (str/Path) or bytes; POSTs as multipart.
        if isinstance(source, (str, Path)):
            with open(source, "rb") as f:
                files = {"file": (Path(source).name, f.read())}
        else:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(source)
                files = {"file": (f"upload{suffix}", open(tmp.name, "rb").read())}
        r = requests.post(
            f"{TRANSCRIPTION_URL}/transcribe",
            headers=_HEADERS, files=files, timeout=_TIMEOUT,
        )
        r.raise_for_status()
        return r.json().get("text", "")

    def transcribe_detailed(self, source, suffix: str = ".mp3"):
        # HTTP transcription service currently returns text only; segments
        # aren't serialized across the wire yet. Wrap the text response into
        # an empty-segments TranscriptionDetails so callers can fall back.
        from . import audio as audio_mod  # local import to avoid cycles
        text = self.transcribe(source, suffix=suffix)
        return audio_mod.TranscriptionDetails(text=text, segments=[], language=None)


class HttpProcessor:
    def generate(self, content_type, context, provider, model, prompt=None,
                 knowledge_base=None, max_tokens=None, user=None,
                 rag_mode="auto"):
        payload = {
            "content_type": content_type,
            "context": context,
            "provider": provider,
            "model": model,
            "prompt": prompt,
            "knowledge_base": knowledge_base,
            "max_tokens": max_tokens,
            "user": user,
            "rag_mode": rag_mode,
        }
        r = requests.post(
            f"{PROCESSING_URL}/generate",
            headers={**_HEADERS, "Content-Type": "application/json"},
            json=payload, timeout=_TIMEOUT,
        )
        r.raise_for_status()
        return r.json().get("result")

    def run_pipeline(self, transcript, provider, model, prompts=None,
                     knowledge_base=None, progress: Optional[Callable] = None,
                     cleanup: bool = True, chapters: bool = True,
                     segments: Optional[list] = None,
                     agentic: bool = False, fact_check: bool = False,
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
                     personas: Optional[list] = None,
                     checkpoint: Optional[Callable] = None):
        payload = {
            "transcript": transcript,
            "provider": provider,
            "model": model,
            "prompts": prompts,
            "knowledge_base": knowledge_base,
            "cleanup": cleanup,
            "chapters": chapters,
            "segments": segments,
            "agentic": agentic,
            "fact_check": fact_check,
            "generate_images": generate_images,
            "image_style": image_style,
            "image_aspect_ratio": image_aspect_ratio,
            "image_model": image_model,
            "image_output_dir": image_output_dir,
            "article_length_words": article_length_words,
            "user": user,
            "rag_mode": rag_mode,
            "compare_provider": compare_provider,
            "compare_model": compare_model,
            "personas": personas,
        }
        r = requests.post(
            f"{PROCESSING_URL}/pipeline",
            headers={**_HEADERS, "Content-Type": "application/json"},
            json=payload, timeout=_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        return pipeline_mod.PipelineResult(
            wisdom=data.get("wisdom"),
            outline=data.get("outline"),
            social_posts=data.get("social_posts"),
            image_prompts=data.get("image_prompts"),
            article=data.get("article"),
            raw_transcript=data.get("raw_transcript"),
            cleaned_transcript=data.get("cleaned_transcript"),
            chapters=data.get("chapters") or [],
            article_draft=data.get("article_draft"),
            article_critique=data.get("article_critique"),
            fact_check_flags=data.get("fact_check_flags") or [],
            generated_images=data.get("generated_images") or [],
            article_compare=data.get("article_compare"),
            compare_label=data.get("compare_label"),
            persona_articles=data.get("persona_articles") or [],
        )


class HttpStorage:
    def save(self, bundle: notion_mod.ContentBundle) -> Optional[str]:
        payload = {
            "title": bundle.title,
            "transcript": bundle.transcript,
            "wisdom": bundle.wisdom,
            "outline": bundle.outline,
            "social_content": bundle.social_content,
            "image_prompts": bundle.image_prompts,
            "article": bundle.article,
            "summary": bundle.summary,
            "tags": bundle.tags,
            "audio_filename": bundle.audio_filename,
            "models_used": bundle.models_used,
            "chapters": bundle.chapters,
            "article_compare": bundle.article_compare,
            "compare_label": bundle.compare_label,
            "persona_articles": bundle.persona_articles,
            "article_critique": bundle.article_critique,
            "fact_check_flags": bundle.fact_check_flags,
            "fact_check_ran": bundle.fact_check_ran,
            "run_metrics": bundle.run_metrics,
            "source_receipts": bundle.source_receipts,
        }
        r = requests.post(
            f"{STORAGE_URL}/save",
            headers={**_HEADERS, "Content-Type": "application/json"},
            json=payload, timeout=_TIMEOUT,
        )
        r.raise_for_status()
        return r.json().get("url")
