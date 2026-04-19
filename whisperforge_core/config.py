"""Runtime configuration for WhisperForge.

Loads API keys from environment (via .env if present), defines the supported
LLM provider/model catalog, and exposes default prompt templates used when a
user hasn't customized their own. Single source of truth for every deployment
mode.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# --- API keys / credentials ------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
SERVICE_TOKEN = os.getenv("SERVICE_TOKEN")

# --- Service URLs (used when DEPLOY_MODE=services) -------------------------
DEPLOY_MODE = os.getenv("DEPLOY_MODE", "direct")  # "direct" | "services"
TRANSCRIPTION_URL = os.getenv("TRANSCRIPTION_URL", "http://transcription:8000")
PROCESSING_URL = os.getenv("PROCESSING_URL", "http://processing:8000")
STORAGE_URL = os.getenv("STORAGE_URL", "http://storage:8000")

# --- Local model runtimes --------------------------------------------------
# Ollama exposes an OpenAI-compatible API on localhost by default.
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")

# Transcription backend: "openai" (cloud Whisper API), "mlx" (local Apple
# Silicon via mlx-whisper), or "whisper_cpp" (local via whisper.cpp binary).
TRANSCRIPTION_BACKEND = os.getenv("TRANSCRIPTION_BACKEND", "openai")
# HF repo or local path for mlx-whisper — "-base-mlx" is tiny/fast,
# "-medium-mlx" is the accuracy sweet spot, "-large-v3-turbo-mlx" is best.
MLX_WHISPER_MODEL = os.getenv(
    "MLX_WHISPER_MODEL", "mlx-community/whisper-medium-mlx"
)

# --- Paths -----------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = PROJECT_ROOT / "prompts"
CACHE_DIR = Path(os.getenv("WHISPERFORGE_CACHE_DIR", PROJECT_ROOT / ".cache"))

# --- Whisper + provider catalog -------------------------------------------
WHISPER_MODEL = "whisper-1"
DEFAULT_CHUNK_TARGET_MB = 25

LLM_MODELS = {
    "OpenAI": {
        "GPT-4 (Most Capable)": "gpt-4",
        "GPT-4 Turbo": "gpt-4-turbo-preview",
        "GPT-3.5 Turbo (Faster)": "gpt-3.5-turbo",
    },
    "Anthropic": {
        "Claude 3 Opus": "claude-3-opus-20240229",
        "Claude 3 Sonnet": "claude-3-sonnet-20240229",
        "Claude 3 Haiku": "claude-3-haiku-20240307",
    },
    # Ollama provider — OpenAI-compatible local inference. The model list is
    # populated dynamically by llm.discover_ollama_models() when the UI loads,
    # so new models you `ollama pull` show up without code changes. This dict
    # is a fallback/default for when Ollama is offline.
    "Ollama (local)": {
        "Llama 3": "llama3:latest",
    },
}

# Default prompts used when a user has no custom prompt on disk.
DEFAULT_PROMPTS = {
    "wisdom_extraction": (
        "Extract key insights, lessons, and wisdom from the transcript. "
        "Focus on actionable takeaways and profound realizations."
    ),
    "summary": (
        "## Summary\n"
        "Create a concise summary of the main points and key messages in the "
        "transcript. Capture the essence of the content in a few paragraphs."
    ),
    "outline_creation": (
        "Create a detailed outline for an article or blog post based on the "
        "transcript and extracted wisdom. Include major sections and subsections."
    ),
    "social_media": (
        "Generate engaging social media posts for different platforms "
        "(Twitter, LinkedIn, Instagram) based on the key insights."
    ),
    "image_prompts": (
        "Create detailed image generation prompts that visualize the key "
        "concepts and metaphors from the content."
    ),
    "article_writing": (
        "Write a comprehensive article based on the provided outline and "
        "wisdom. Maintain a clear narrative flow and engaging style."
    ),
    "seo_analysis": (
        "Analyze the content from an SEO perspective and provide optimization "
        "recommendations for better search visibility while maintaining content quality."
    ),
}

CONTENT_TYPES = list(DEFAULT_PROMPTS.keys())
