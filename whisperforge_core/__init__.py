"""WhisperForge core logic package.

Pure-Python modules for audio transcription, LLM content generation, Notion
export, prompt management, capture records, KB audits, caching, and logging. Importable from both the
Streamlit monolith and the FastAPI microservices — must NOT import streamlit.
"""

from . import adapters, audio, cache, captures, composition_review, config, cost, export, history, images, kb_audit, llm, notion, pipeline, prompts, recipes, run_artifacts, scorecards
from . import logging as logging_module

__all__ = [
    "adapters",
    "audio",
    "cache",
    "captures",
    "composition_review",
    "config",
    "cost",
    "export",
    "history",
    "images",
    "kb_audit",
    "llm",
    "logging_module",
    "notion",
    "pipeline",
    "prompts",
    "recipes",
    "run_artifacts",
    "scorecards",
]
