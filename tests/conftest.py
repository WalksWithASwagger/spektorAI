"""Shared pytest setup — dummy env vars so imports don't require real keys."""

import os

for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "NOTION_API_KEY",
            "NOTION_DATABASE_ID", "SERVICE_TOKEN"):
    os.environ.setdefault(key, "dummy")
