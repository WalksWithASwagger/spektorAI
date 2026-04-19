"""Logging setup for WhisperForge.

Restored from the pattern in the retired old_app.py. Log to both stderr (for
Streamlit + docker container stdout) and an optional file when the
WHISPERFORGE_LOG_FILE env var is set.
"""

import logging
import os

_configured = False


def get_logger(name: str = "whisperforge") -> logging.Logger:
    """Return a configured logger. Safe to call multiple times."""
    global _configured
    if not _configured:
        handlers = [logging.StreamHandler()]
        log_file = os.getenv("WHISPERFORGE_LOG_FILE")
        if log_file:
            handlers.append(logging.FileHandler(log_file))
        logging.basicConfig(
            level=os.getenv("WHISPERFORGE_LOG_LEVEL", "INFO"),
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=handlers,
        )
        _configured = True
    return logging.getLogger(name)
