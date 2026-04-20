"""In-memory vector store with on-disk persistence + mtime invalidation.

Pure numpy + pickle — no FAISS dependency. For Kris's 5-doc KB, brute-
force cosine over ~50 chunks is sub-millisecond. We can swap to FAISS if
KBs grow past ~5000 chunks (the plan documents that threshold).

Store layout on disk::

    .cache/rag/<user>/<embed_model_hash>/
        index.npy        # float32 (N, dim), L2-normalized
        chunks.pkl       # list[Chunk] in matching order
        manifest.json    # {built_at, kb_mtime, chunk_count, model_name}

Invalidation: rebuild whenever any KB file's mtime exceeds ``kb_mtime``
in the manifest. Cheap stat() call on every ``ensure_built()``.
"""

from __future__ import annotations

import json
import pickle
from dataclasses import asdict
from pathlib import Path
from time import time
from typing import List

import numpy as np

from ..config import CACHE_DIR, PROMPTS_DIR
from ..logging import get_logger
from . import chunker, embedder
from .chunker import Chunk

logger = get_logger(__name__)


def _store_dir(user: str) -> Path:
    return CACHE_DIR / "rag" / user / embedder.model_id_hash()


def _kb_dir(user: str) -> Path:
    return PROMPTS_DIR / user / "knowledge_base"


def _max_kb_mtime(kb_dir: Path) -> float:
    """Max mtime across all KB files. 0 if no files. Used as the
    invalidation signal: any file edit triggers a rebuild."""
    if not kb_dir.exists():
        return 0.0
    mtimes = [
        p.stat().st_mtime for p in kb_dir.iterdir()
        if p.suffix.lower() in {".md", ".txt"} and not p.name.startswith(".")
    ]
    return max(mtimes) if mtimes else 0.0


class KBStore:
    """Per-user vector store. Built lazily, persisted to disk, invalidated
    on KB edits.

    Usage::

        store = KBStore(user="KK")
        store.ensure_built()                       # idempotent
        hits = store.search("voice and tone", k=5) # [(chunk, score), ...]
    """

    def __init__(self, user: str):
        self.user = user
        self.dir = _store_dir(user)
        self.kb_dir = _kb_dir(user)
        self.index: np.ndarray | None = None
        self.chunks: List[Chunk] = []
        self._loaded = False

    # ---- Public API -----------------------------------------------------

    def ensure_built(self) -> None:
        """Load from disk, or rebuild from KB files if stale/missing."""
        if self._is_fresh():
            self._load()
            return
        self._build()

    def search(self, query: str, k: int = 5) -> List[tuple[Chunk, float]]:
        """Return up to ``k`` (chunk, score) pairs ranked by descending
        cosine similarity. Score is in [-1, 1]; >0.5 is generally relevant."""
        self.ensure_built()
        if self.index is None or len(self.chunks) == 0:
            return []
        q = embedder.embed([query])             # (1, dim)
        scores = (self.index @ q.T).flatten()    # (N,)
        # argpartition is O(N), then we sort the top-k slice for stable order
        k = min(k, len(self.chunks))
        top = np.argpartition(-scores, k - 1)[:k]
        top_sorted = top[np.argsort(-scores[top])]
        return [(self.chunks[i], float(scores[i])) for i in top_sorted]

    def chunk_count(self) -> int:
        if not self._loaded:
            self.ensure_built()
        return len(self.chunks)

    # ---- Internal -------------------------------------------------------

    def _manifest_path(self) -> Path:
        return self.dir / "manifest.json"

    def _is_fresh(self) -> bool:
        """True if a persisted index exists and isn't stale vs the KB."""
        mp = self._manifest_path()
        if not mp.exists():
            return False
        try:
            manifest = json.loads(mp.read_text())
        except (OSError, json.JSONDecodeError):
            return False
        return manifest.get("kb_mtime", 0) >= _max_kb_mtime(self.kb_dir) - 1e-3

    def _load(self) -> None:
        try:
            self.index = np.load(self.dir / "index.npy")
            with open(self.dir / "chunks.pkl", "rb") as f:
                self.chunks = pickle.load(f)
            self._loaded = True
            logger.info("loaded %d KB chunks from %s",
                        len(self.chunks), self.dir)
        except (OSError, pickle.PickleError) as e:
            logger.warning("load failed (%s); rebuilding", e)
            self._build()

    def _build(self) -> None:
        t0 = time()
        chunks = chunker.chunk_kb_dir(self.kb_dir)
        if not chunks:
            self.chunks, self.index, self._loaded = [], None, True
            return
        texts = [c.text for c in chunks]
        index = embedder.embed(texts)
        self.chunks = chunks
        self.index = index
        self._persist()
        self._loaded = True
        logger.info(
            "built KB index for %s: %d chunks in %.2fs (model=%s)",
            self.user, len(chunks), time() - t0, embedder.model_name(),
        )

    def _persist(self) -> None:
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
            np.save(self.dir / "index.npy", self.index)
            with open(self.dir / "chunks.pkl", "wb") as f:
                pickle.dump(self.chunks, f)
            manifest = {
                "built_at": time(),
                "kb_mtime": _max_kb_mtime(self.kb_dir),
                "chunk_count": len(self.chunks),
                "model_name": embedder.model_name(),
            }
            self._manifest_path().write_text(json.dumps(manifest))
        except (OSError, pickle.PickleError) as e:
            logger.warning("persist failed (%s)", e)


def reset_user(user: str) -> None:
    """Delete the on-disk index for one user. Forces rebuild next query."""
    import shutil
    d = _store_dir(user)
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)
