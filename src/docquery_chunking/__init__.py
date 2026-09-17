"""ParsedDocument -> list[Chunk]. One of DocQuery's independently versioned
pipeline submodules."""

from __future__ import annotations

from docquery_chunking.chunker import StructureAwareChunker
from docquery_chunking.config import ChunkingConfig
from docquery_chunking.factory import build_chunker

__all__ = [
    "ChunkingConfig",
    "StructureAwareChunker",
    "build_chunker",
]
