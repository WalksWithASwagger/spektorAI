"""Deployment adapters — direct in-process calls vs HTTP to microservices.

Selected by the DEPLOY_MODE env var (see config.DEPLOY_MODE). UI code uses
``get_adapters()`` and doesn't need to know which backend is active.

- ``direct`` (default) — import + call whisperforge_core modules directly.
- ``services`` — POST to FastAPI services listed in config. Used inside the
  frontend container under docker-compose.

Direct mode is the primary production surface. The HTTP implementations exist
for services mode, but they must stay in lockstep with the FastAPI schemas
before services mode can claim full feature parity.
"""

from dataclasses import dataclass
from typing import Callable, Dict, Optional, Protocol

from . import audio as audio_mod
from . import llm as llm_mod
from . import notion as notion_mod
from . import pipeline as pipeline_mod
from .config import DEPLOY_MODE


class Transcriber(Protocol):
    def transcribe(self, source, suffix: str = ".mp3", progress=None) -> str: ...

    def transcribe_detailed(
        self, source, suffix: str = ".mp3"
    ) -> audio_mod.TranscriptionDetails: ...


class Processor(Protocol):
    def generate(
        self,
        content_type: str,
        context: Dict[str, str],
        provider: str,
        model: str,
        prompt: Optional[str] = None,
        knowledge_base: Optional[Dict[str, str]] = None,
        max_tokens: Optional[int] = None,
        user: Optional[str] = None,
        rag_mode: str = "auto",
    ) -> Optional[str]: ...

    def run_pipeline(
        self,
        transcript: str,
        provider: str,
        model: str,
        prompts: Optional[Dict[str, str]] = None,
        knowledge_base: Optional[Dict[str, str]] = None,
        progress: Optional[Callable] = None,
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
        personas: Optional[list] = None,
        checkpoint: Optional[Callable] = None,
    ) -> pipeline_mod.PipelineResult: ...


class Storage(Protocol):
    def save(self, bundle: notion_mod.ContentBundle) -> Optional[str]: ...


# --- Local (in-process) implementations ------------------------------------

class LocalTranscriber:
    def transcribe(self, source, suffix: str = ".mp3", progress=None) -> str:
        return audio_mod.transcribe_audio(source, suffix=suffix, progress=progress)

    def transcribe_detailed(
        self, source, suffix: str = ".mp3"
    ) -> audio_mod.TranscriptionDetails:
        return audio_mod.transcribe_audio_detailed(source, suffix=suffix)


class LocalProcessor:
    def generate(self, content_type, context, provider, model, prompt=None,
                 knowledge_base=None, max_tokens=None, user=None,
                 rag_mode="auto"):
        return llm_mod.generate(content_type, context, provider, model,
                                prompt=prompt, knowledge_base=knowledge_base,
                                max_tokens=max_tokens, user=user,
                                rag_mode=rag_mode)

    def run_pipeline(self, transcript, provider, model, prompts=None,
                     knowledge_base=None, progress=None,
                     cleanup=True, chapters=True, segments=None,
                     agentic=False, fact_check=False,
                     generate_images=False, image_style=None,
                     image_aspect_ratio="16:9",
                     image_model="gemini-2.5-flash-image",
                     image_output_dir=None,
                     article_length_words=1500,
                     user=None, rag_mode="auto",
                     compare_provider=None, compare_model=None,
                     personas=None, checkpoint=None):
        return pipeline_mod.run(
            transcript, provider, model, prompts=prompts,
            knowledge_base=knowledge_base, progress=progress,
            cleanup=cleanup, chapters=chapters,
            segments=segments, agentic=agentic, fact_check=fact_check,
            generate_images=generate_images, image_style=image_style,
            image_aspect_ratio=image_aspect_ratio, image_model=image_model,
            image_output_dir=image_output_dir,
            article_length_words=article_length_words,
            user=user, rag_mode=rag_mode,
            compare_provider=compare_provider, compare_model=compare_model,
            personas=personas,
            checkpoint=checkpoint,
        )


class LocalStorage:
    def save(self, bundle: notion_mod.ContentBundle) -> Optional[str]:
        return notion_mod.create_page(bundle)


# --- Bundle -----------------------------------------------------------------

@dataclass
class Adapters:
    transcriber: Transcriber
    processor: Processor
    storage: Storage


def get_adapters() -> Adapters:
    """Return the active adapter bundle based on DEPLOY_MODE."""
    if DEPLOY_MODE == "services":
        from . import http_adapters
        return Adapters(
            transcriber=http_adapters.HttpTranscriber(),
            processor=http_adapters.HttpProcessor(),
            storage=http_adapters.HttpStorage(),
        )
    return Adapters(
        transcriber=LocalTranscriber(),
        processor=LocalProcessor(),
        storage=LocalStorage(),
    )
