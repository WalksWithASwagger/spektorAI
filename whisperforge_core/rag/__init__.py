"""Retrieval-augmented KB injection.

Phase 1: chunker + embedder + store. Pure-Python building blocks, no
integration into the LLM pipeline yet — that's Phase 2.
"""

from . import benchmark, chunker, embedder, retriever, store
from .benchmark import benchmark_all_stages, compare_kb_modes
from .chunker import Chunk, chunk_kb_dir, chunk_file
from .retriever import format_block, retrieve, should_engage
from .store import KBStore, reset_user

__all__ = [
    "benchmark", "chunker", "embedder", "retriever", "store",
    "Chunk", "chunk_kb_dir", "chunk_file",
    "KBStore", "reset_user",
    "format_block", "retrieve", "should_engage",
    "compare_kb_modes", "benchmark_all_stages",
]
