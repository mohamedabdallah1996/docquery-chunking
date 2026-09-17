"""Resolves the full chunking config into a ready-to-use chunker.

The one place "which strategy" gets decided -- callers never construct
StructureAwareChunker directly. Single-branch until a second strategy exists.
"""

from __future__ import annotations

from typing import Any

from docquery_chunking.chunker import StructureAwareChunker
from docquery_chunking.config import ChunkingConfig


def build_chunker(config: dict[str, Any]) -> StructureAwareChunker:
    """Build the configured chunker from the orchestrator's full
    `{"chunking": {...}}`-shaped config."""
    parsed = ChunkingConfig.model_validate(config["chunking"])
    return StructureAwareChunker(parsed)
