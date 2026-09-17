"""Structure-aware chunking: split a ParsedDocument into Chunks while
preserving its heading hierarchy.

One concrete class, no strategy hierarchy -- this is the only chunking
approach today. If a second one is ever actually built, factor the shared
sequence out into a base class *then*, when there's a second real
implementation to justify it.
"""

from __future__ import annotations

from docquery_core import Chunk, ParsedDocument

from docquery_chunking.components.markdown_parser import MarkdownParser
from docquery_chunking.components.section_builder import SectionBuilder
from docquery_chunking.components.section_chunker import SectionChunker
from docquery_chunking.components.text_splitter import TextSplitter
from docquery_chunking.config import ChunkingConfig


class StructureAwareChunker:
    """Chunk a parsed document while preserving heading hierarchy."""

    def __init__(self, config: ChunkingConfig) -> None:
        self._parser = MarkdownParser()
        self._section_builder = SectionBuilder(min_section_tokens=config.min_section_tokens)
        self._section_chunker = SectionChunker(
            splitter=TextSplitter(target_tokens=config.target_tokens)
        )

    def chunk(self, document: ParsedDocument) -> list[Chunk]:
        """Convert a parsed document into retrieval chunks, in document order."""
        blocks = self._parser.parse(document)
        sections = self._section_builder.build(blocks)

        chunks: list[Chunk] = []
        for section in sections:
            chunks.extend(self._section_chunker.chunk(document=document, section=section))
        return chunks
