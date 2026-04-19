"""Deployment adapters — direct in-process calls vs HTTP to microservices.

Selected by the DEPLOY_MODE env var (see config.DEPLOY_MODE). UI code uses
``get_adapters()`` and doesn't need to know which backend is active.

- ``direct`` (default) — import + call whisperforge_core modules directly.
- ``services`` — POST to FastAPI services listed in config. Used inside the
  frontend container under docker-compose.

Phase B populates this only enough to keep the monolith working; Phase C fills
in the HTTP implementations once the services are resurrected.
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
    ) -> Optional[str]: ...

    def run_pipeline(
        self,
        transcript: str,
        provider: str,
        model: str,
        prompts: Optional[Dict[str, str]] = None,
        knowledge_base: Optional[Dict[str, str]] = None,
        progress: Optional[Callable] = None,
        segments: Optional[list] = None,
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
    def generate(self, content_type, context, provider, model, prompt=None, knowledge_base=None):
        return llm_mod.generate(content_type, context, provider, model,
                                prompt=prompt, knowledge_base=knowledge_base)

    def run_pipeline(self, transcript, provider, model, prompts=None,
                     knowledge_base=None, progress=None, segments=None):
        return pipeline_mod.run(
            transcript, provider, model, prompts=prompts,
            knowledge_base=knowledge_base, progress=progress,
            segments=segments,
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
        # Phase C will populate Http* implementations here.
        from . import http_adapters  # type: ignore  # lazy import; created in Phase C
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
