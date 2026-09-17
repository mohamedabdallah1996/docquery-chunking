"""Resolves the full chunking module config into a ready-to-use chunker.

This is the one place "which strategy" gets decided -- callers should never
construct StructureAwareChunker directly. Only one strategy exists today;
this stays a single-branch factory until a second one actually exists to
select between.
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
