"""Retrieval-augmented KB injection.

Phase 1: chunker + embedder + store. Pure-Python building blocks, no
integration into the LLM pipeline yet — that's Phase 2.
"""

from . import chunker, embedder, store
from .chunker import Chunk, chunk_kb_dir, chunk_file
from .store import KBStore, reset_user

__all__ = [
    "chunker", "embedder", "store",
    "Chunk", "chunk_kb_dir", "chunk_file",
    "KBStore", "reset_user",
]
