"""Converts a ParsedDocument into a flat sequence of MarkdownBlocks.

This parser is responsible only for understanding Markdown structure -- it
does not know anything about sections, chunk sizes, or embeddings.
"""

from __future__ import annotations

from docquery_core import ParsedDocument, ParsedPage
from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode
from mdit_py_plugins.gfm import gfm_plugin

from docquery_chunking.models import MarkdownBlock


class MarkdownParser:
    def __init__(self) -> None:
        self._markdown = MarkdownIt().use(gfm_plugin)

    def parse(self, document: ParsedDocument) -> list[MarkdownBlock]:
        """Parse every page into one flat, document-ordered list of blocks.

        Each page is parsed independently, but page numbers are preserved on
        each block so later stages can associate a chunk with its source page.
        """
        blocks: list[MarkdownBlock] = []
        for page in document.pages:
            blocks.extend(self.parse_page(page))
        return blocks

    def parse_page(self, page: ParsedPage) -> list[MarkdownBlock]:
        tree = SyntaxTreeNode(self._markdown.parse(page.markdown))
        blocks: list[MarkdownBlock] = []
        for node in tree.children:
            blocks.extend(self._parse_node(node, page.page_number))
        return blocks

    def _parse_node(self, node: SyntaxTreeNode, page: int) -> list[MarkdownBlock]:
        match node.type:
            case "heading":
                return [self._parse_heading(node, page)]
            case "paragraph":
                return self._parse_paragraph(node, page)
            case "bullet_list" | "ordered_list":
                return self._parse_list(node, page)
            case "table":
                return [self._parse_table(node, page)]
            case "fence":
                return [self._parse_code(node, page)]
            case _:
                return []  # unsupported markdown blocks are ignored

    def _parse_heading(self, node: SyntaxTreeNode, page: int) -> MarkdownBlock:
        return MarkdownBlock(
            kind="heading",
            page=page,
            level=int(node.tag[1:]),
            text=self._inline_text(node),
        )

    def _parse_paragraph(self, node: SyntaxTreeNode, page: int) -> list[MarkdownBlock]:
        text = self._inline_text(node).strip()
        if not text:
            return []
        return [MarkdownBlock(kind="text", page=page, text=text)]

    def _parse_list(self, node: SyntaxTreeNode, page: int) -> list[MarkdownBlock]:
        blocks: list[MarkdownBlock] = []
        for item in node.children:
            if not item.children:
                continue
            text = self._inline_text(item.children[0]).strip()
            if not text:
                continue
            blocks.append(MarkdownBlock(kind="list_item", page=page, text=text))
        return blocks

    def _parse_table(self, node: SyntaxTreeNode, page: int) -> MarkdownBlock:
        header: list[str] = []
        rows: list[list[str]] = []

        for section in node.children:
            for row in section.children:
                cells = [self._inline_text(cell) for cell in row.children]
                if section.type == "thead":
                    header = cells
                else:
                    rows.append(cells)

        return MarkdownBlock(kind="table", page=page, table_header=header, table_rows=rows)

    def _parse_code(self, node: SyntaxTreeNode, page: int) -> MarkdownBlock:
        """A fence node carries its raw text directly on `.content` -- unlike
        headings/paragraphs/tables, there's no inline child to unwrap."""
        return MarkdownBlock(kind="code", page=page, text=node.content)

    @staticmethod
    def _inline_text(node: SyntaxTreeNode) -> str:
        if not node.children:
            return ""
        return node.children[0].content
