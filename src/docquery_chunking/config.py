"""Configuration for the chunking package."""

from __future__ import annotations

from pydantic import BaseModel


class ChunkingConfig(BaseModel):
    target_tokens: int = 500  # soft size budget a text/table chunk is packed towards
    min_section_tokens: int = 30  # sections smaller than this merge into the next one
