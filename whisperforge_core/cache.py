"""File-hash pickle cache for transcriptions and LLM outputs.

Restored from old_app.py with a safer key: sha256(file_bytes) + model + prompt_hash.
Keying on the file alone produced stale wisdom when prompts changed.

Disabled by default so runs stay fresh. Enable by setting
``WHISPERFORGE_CACHE=1`` (or ``true``/``yes``/``on``). Clear with
``cache.clear()`` or by deleting the ``.cache/`` directory.
"""

import hashlib
import os
import pickle
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

from .config import CACHE_DIR
from .logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def enabled() -> bool:
    """True when the WHISPERFORGE_CACHE env flag opts the user in."""
    return os.getenv("WHISPERFORGE_CACHE", "").lower() in ("1", "true", "yes", "on")


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


def cached_or_compute(key: str, compute: Callable[[], T]) -> T:
    """If caching is enabled and ``key`` is in cache, return the cached value.
    Otherwise call ``compute()``, store its result (when non-None/non-empty),
    and return it. When caching is disabled, this is equivalent to just
    calling ``compute()`` — zero overhead, zero behavior change."""
    if not enabled():
        return compute()

    hit = get(key)
    if hit is not None:
        logger.info("cache HIT %s", key[:8])
        return hit

    logger.info("cache MISS %s", key[:8])
    value = compute()
    # Never persist falsy sentinel values — an empty transcript or None LLM
    # output is almost always an error state, and caching it would wedge the
    # user into replaying the failure.
    if value:
        put(key, value)
    return value
