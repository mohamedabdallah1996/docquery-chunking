"""Build logical document sections from markdown blocks.

A section is defined by the document's heading hierarchy. Small sections that
contain only a heading and a small amount of text are merged into the
following section to avoid creating low-value chunks.
"""

from __future__ import annotations

from docquery_chunking.models import DocumentSection, MarkdownBlock
from docquery_chunking.utils import count_tokens


class SectionBuilder:
    def __init__(self, *, min_section_tokens: int) -> None:
        self._min_section_tokens = min_section_tokens

    def build(self, blocks: list[MarkdownBlock]) -> list[DocumentSection]:
        sections = self._group_by_headings(blocks)
        return self._merge_small_sections(sections)

    def _group_by_headings(self, blocks: list[MarkdownBlock]) -> list[DocumentSection]:
        """Group blocks by heading hierarchy, using a stack so nested headings
        (H1 > H2 > H3) are represented correctly."""
        sections: list[DocumentSection] = [DocumentSection(path=[])]
        heading_stack: list[tuple[int, str]] = []

        for block in blocks:
            if block.kind == "heading":
                assert block.level is not None
                while heading_stack and heading_stack[-1][0] >= block.level:
                    heading_stack.pop()
                heading_stack.append((block.level, block.text))
                sections.append(DocumentSection(path=[title for _, title in heading_stack]))
                continue

            sections[-1].blocks.append(block)

        return [section for section in sections if section.blocks or section.path]

    def _merge_small_sections(self, sections: list[DocumentSection]) -> list[DocumentSection]:
        """Merge very small text sections into the following section.

        Sections containing a table or code block are never merged, since
        those are meaningful regardless of their size.
        """
        merged: list[DocumentSection] = []
        carried_blocks: list[MarkdownBlock] = []
        carried_headings: list[str] = []  # leaf headings merged away so far, oldest first

        for index, section in enumerate(sections):
            blocks = carried_blocks + section.blocks
            carried_blocks = []
            is_last = index == len(sections) - 1

            if not is_last and self._should_merge(blocks):
                carried_blocks = blocks
                # Skip empty headings (e.g. "# Title" right before "## A") --
                # nothing was merged away, so there's nothing to attribute.
                if section.path and section.blocks:
                    carried_headings.append(section.path[-1])
                continue

            path = section.path
            if carried_headings and path:
                path = [*path[:-1], " / ".join([*carried_headings, path[-1]])]
            carried_headings = []

            merged.append(DocumentSection(path=path, blocks=blocks))

        if carried_blocks:
            if merged:
                merged[-1].blocks.extend(carried_blocks)
            else:
                merged.append(DocumentSection(path=[], blocks=carried_blocks))

        return merged

    def _should_merge(self, blocks: list[MarkdownBlock]) -> bool:
        # A table or code block is meaningful regardless of size.
        if any(block.kind in ("table", "code") for block in blocks):
            return False
        return self._count_tokens(blocks) < self._min_section_tokens

    @staticmethod
    def _count_tokens(blocks: list[MarkdownBlock]) -> int:
        total = 0
        for block in blocks:
            match block.kind:
                case "text" | "list_item":
                    total += count_tokens(block.text)
                case "table":
                    total += sum(count_tokens(" ".join(row)) for row in block.table_rows or [])
        return total
