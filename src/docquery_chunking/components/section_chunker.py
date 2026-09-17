"""Convert document sections into Chunk objects.

A section is processed sequentially, preserving the original document order.
Text and list items are accumulated into runs and split together; tables and
code blocks are always emitted as their own standalone chunk(s).
"""

from __future__ import annotations

from docquery_core import Chunk, ChunkType, ParsedDocument

from docquery_chunking.components.text_splitter import TextSplitter
from docquery_chunking.models import DocumentSection, MarkdownBlock
from docquery_chunking.utils import stable_id


class SectionChunker:
    def __init__(self, *, splitter: TextSplitter) -> None:
        self._splitter = splitter

    def chunk(self, *, document: ParsedDocument, section: DocumentSection) -> list[Chunk]:
        parent_chunk_id = stable_id(document.doc_id, "/".join(section.path))

        chunks: list[Chunk] = []
        text_run: list[MarkdownBlock] = []

        def flush_text() -> None:
            if not text_run:
                return
            chunks.extend(
                self._build_text_chunks(
                    document=document,
                    section=section,
                    parent_chunk_id=parent_chunk_id,
                    blocks=list(text_run),
                )
            )
            text_run.clear()

        for block in section.blocks:
            match block.kind:
                case "text" | "list_item":
                    text_run.append(block)

                case "table":
                    flush_text()
                    for table in self._splitter.split_table(
                        block.table_header or [], block.table_rows or []
                    ):
                        chunks.append(
                            self._make_chunk(
                                document=document,
                                section=section,
                                parent_chunk_id=parent_chunk_id,
                                page=block.page,
                                chunk_type="table",
                                content=table,
                            )
                        )

                case "code":
                    flush_text()
                    chunks.append(
                        self._make_chunk(
                            document=document,
                            section=section,
                            parent_chunk_id=parent_chunk_id,
                            page=block.page,
                            chunk_type="code",
                            content=block.text,
                        )
                    )

        flush_text()
        return chunks

    def _build_text_chunks(
        self,
        *,
        document: ParsedDocument,
        section: DocumentSection,
        parent_chunk_id: str,
        blocks: list[MarkdownBlock],
    ) -> list[Chunk]:
        is_list = all(block.kind == "list_item" for block in blocks)
        texts = [block.text for block in blocks]
        page = blocks[0].page

        return [
            self._make_chunk(
                document=document,
                section=section,
                parent_chunk_id=parent_chunk_id,
                page=page,
                chunk_type="list" if is_list else "text",
                content=text,
            )
            for text in self._splitter.split_text_blocks(texts, is_list=is_list)
        ]

    def _make_chunk(
        self,
        *,
        document: ParsedDocument,
        section: DocumentSection,
        parent_chunk_id: str,
        page: int,
        chunk_type: ChunkType,
        content: str,
    ) -> Chunk:
        return Chunk(
            chunk_id=stable_id(document.doc_id, chunk_type, str(page), content),
            doc_id=document.doc_id,
            page_number=page,
            chunk_type=chunk_type,
            section_path=tuple(section.path),
            content=content,
            parent_chunk_id=parent_chunk_id,
        )
