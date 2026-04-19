"""File-hash pickle cache for transcriptions and LLM outputs.

Restored from old_app.py with a safer key: sha256(file_bytes) + model + prompt_hash.
Keying on the file alone produced stale wisdom when prompts changed.
"""

import hashlib
import pickle
from pathlib import Path
from typing import Any, Optional

from .config import CACHE_DIR
from .logging import get_logger

logger = get_logger(__name__)


def _ensure_cache_dir() -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


def file_hash(path: str | Path) -> str:
    """sha256 of file bytes. Streams so it handles large audio without OOM."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_key(parts: list[str]) -> str:
    """Combine components into a cache key."""
    joined = "||".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _cache_path(key: str) -> Path:
    return _ensure_cache_dir() / f"{key}.pkl"


def get(key: str) -> Optional[Any]:
    path = _cache_path(key)
    if not path.exists():
        return None
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except (OSError, pickle.PickleError) as e:
        logger.warning("Cache read failed for %s: %s", key[:8], e)
        return None


def put(key: str, value: Any) -> None:
    path = _cache_path(key)
    try:
        with open(path, "wb") as f:
            pickle.dump(value, f)
        logger.info("Cache wrote %s (%d bytes)", key[:8], path.stat().st_size)
    except (OSError, pickle.PickleError) as e:
        logger.warning("Cache write failed for %s: %s", key[:8], e)


def clear() -> int:
    """Remove all cache entries. Returns count removed."""
    if not CACHE_DIR.exists():
        return 0
    count = 0
    for path in CACHE_DIR.glob("*.pkl"):
        try:
            path.unlink()
            count += 1
        except OSError:
            pass
    return count
