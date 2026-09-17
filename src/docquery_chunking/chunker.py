"""Structure-aware chunking: ParsedDocument -> Chunks, preserving heading
hierarchy.

One concrete class, no strategy hierarchy -- revisit only once a second
real strategy exists to justify one.
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
            splitter=TextSplitter(
                target_tokens=config.target_tokens,
                min_section_tokens=config.min_section_tokens,
            )
        )

    def chunk(self, document: ParsedDocument) -> list[Chunk]:
        """Convert a parsed document into retrieval chunks, in document order."""
        blocks = self._parser.parse(document)
        sections = self._section_builder.build(blocks)

        chunks: list[Chunk] = []
        for section in sections:
            chunks.extend(self._section_chunker.chunk(document=document, section=section))
        return chunks


def main() -> None:
    """Run the chunker over a demo document and print each resulting chunk.

    Covers: nested headings, a mergeable section, an atomic table, an
    oversized table, a list, code, an oversized paragraph, and a short
    remark trailing one (stays unmerged -- nothing follows it to fold into).
    """
    from docquery_core import ParsedPage

    from docquery_chunking.utils import count_tokens

    long_paragraph = " ".join(f"This is sentence number {i} of the overview." for i in range(80))
    notes_paragraph = " ".join(
        f"This is sentence number {i} of the notes section." for i in range(80)
    )
    compatibility_rows = "\n".join(f"| Model-{i} | Yes |" for i in range(60))

    page_1 = (
        "# Product Manual\n\n"
        "## Introduction\n\n"
        "Short.\n\n"  # below min_section_tokens -- should merge into Overview
        "## Overview\n\n"
        f"{long_paragraph}\n\n"
        "## Specifications\n\n"
        "| Parameter | Value | Unit |\n"
        "| --- | --- | --- |\n"
        "| Weight | 1.2 | kg |\n"
        "| Height | 30 | cm |\n"
    )
    page_2 = (
        "## Compatibility\n\n"
        "| Model | Compatible |\n"
        "| --- | --- |\n"
        f"{compatibility_rows}\n\n"
        "## Installation\n\n"
        "- Unbox the device carefully and lay out all included accessories\n"
        "- Connect the power cable to a grounded outlet before continuing\n"
        "- Press and hold the power button for three seconds to start it\n\n"
        "## Example Code\n\n"
        "```python\n"
        "def install():\n"
        '    print("installing")\n'
        "```\n\n"
        "## Notes\n\n"
        f"{notes_paragraph}\n\n"
        "One final short remark.\n"
    )

    document = ParsedDocument(
        doc_id="demo-manual-001",
        pages=(
            ParsedPage(page_number=1, markdown=page_1),
            ParsedPage(page_number=2, markdown=page_2),
        ),
        status="DONE",
    )

    chunks = StructureAwareChunker(ChunkingConfig()).chunk(document)

    separator = "=" * 78
    print(separator)
    print(f"chunking {document.doc_id!r} ({len(document.pages)} pages) -> {len(chunks)} chunks")
    print(separator)

    counts_by_type: dict[str, int] = {}
    for i, chunk in enumerate(chunks, start=1):
        counts_by_type[chunk.chunk_type] = counts_by_type.get(chunk.chunk_type, 0) + 1

        max_lines, max_line_chars = 20, 300
        lines = chunk.content.splitlines()
        hidden_line_count = max(0, len(lines) - max_lines)

        print(f"\nChunk {i}/{len(chunks)}")
        print(f"  type:      {chunk.chunk_type}")
        print(f"  page:      {chunk.page_number}")
        print(f"  section:   {' > '.join(chunk.section_path) or '(none)'}")
        print(f"  tokens:    {count_tokens(chunk.content)}")
        print(f"  chunk_id:  {chunk.chunk_id}")
        print(f"  parent_id: {chunk.parent_chunk_id}")
        print("  content:")
        for line in lines[:max_lines]:
            if len(line) > max_line_chars:
                line = line[:max_line_chars] + "..."
            print(f"    {line}")
        if hidden_line_count:
            print(f"    ... ({hidden_line_count} more lines)")

    print()
    print(separator)
    print(f"summary: {len(chunks)} chunks total")
    for chunk_type, count in sorted(counts_by_type.items()):
        print(f"  {chunk_type}: {count}")
    print(separator)


if __name__ == "__main__":
    main()
