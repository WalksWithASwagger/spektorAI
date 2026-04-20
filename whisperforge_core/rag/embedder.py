"""Embedding model loader.

Lazy-loads ``sentence-transformers`` only when first called — keeps the
~2-second model load out of cold-start paths that don't need RAG. The
default model (``all-MiniLM-L6-v2``) is already cached on Kris's
machine; the override env var lets power users swap in a stronger model
like ``BAAI/bge-base-en-v1.5`` without code changes.
"""

from __future__ import annotations

import hashlib
import os
from typing import List

import numpy as np

from ..logging import get_logger

logger = get_logger(__name__)

_DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Process-cached model so repeated retrieval calls don't pay the load tax.
_MODEL = None
_MODEL_NAME = None


def model_name() -> str:
    return os.getenv("WF_EMBED_MODEL", _DEFAULT_MODEL)


def model_id_hash() -> str:
    """Short stable hash of the active embedding model — lets the vector
    store key its persisted index by which embedder produced it. Switching
    models invalidates the cache automatically."""
    return hashlib.sha1(model_name().encode("utf-8")).hexdigest()[:10]


def _load() -> "SentenceTransformer":  # type: ignore  # forward ref for lazy import
    global _MODEL, _MODEL_NAME
    name = model_name()
    if _MODEL is None or _MODEL_NAME != name:
        from sentence_transformers import SentenceTransformer
        logger.info("loading embedder %s", name)
        _MODEL = SentenceTransformer(name)
        _MODEL_NAME = name
    return _MODEL


def embed(texts: List[str]) -> np.ndarray:
    """Return an (N, dim) float32 array of L2-normalized embeddings.
    Normalization lets the store use plain dot products instead of
    cosine similarity (numerically identical, faster)."""
    if not texts:
        return np.zeros((0, dim()), dtype=np.float32)
    arr = _load().encode(texts, normalize_embeddings=True)
    return np.asarray(arr, dtype=np.float32)


def dim() -> int:
    """Embedding dimension for the active model. Loads lazily."""
    return _load().get_sentence_embedding_dimension()
