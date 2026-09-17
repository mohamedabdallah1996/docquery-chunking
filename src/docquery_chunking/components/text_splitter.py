"""Splits accumulated text/list-item runs, and oversized tables, into
retrieval-sized chunks.

Text splitting delegates to LangChain's RecursiveCharacterTextSplitter, which
already solves "pack near a token budget, falling back through smaller
separators for anything still oversized" more robustly than a hand-rolled
version would (paragraph -> line -> sentence -> word/character, recursively,
measured against a real tokenizer). Table splitting stays custom: a table
row is atomic in a way no generic text splitter understands, and the header
must be repeated in every split-off piece to stay valid Markdown.
"""

from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter

from docquery_chunking.utils import count_tokens

# Largest-to-smallest split points: keep paragraphs together first, then
# lines, then sentences -- only falling back to raw word/character breaks
# for a single run-on sentence that's still oversized on its own.
_SEPARATORS = ["\n\n", "\n", ". ", "! ", "? ", " ", ""]


class TextSplitter:
    def __init__(self, *, target_tokens: int) -> None:
        self._target_tokens = target_tokens
        self._splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            encoding_name="cl100k_base",
            separators=_SEPARATORS,
            chunk_size=target_tokens,
            chunk_overlap=0,
        )

    def split_text_blocks(self, blocks: list[str], *, is_list: bool = False) -> list[str]:
        """Split a run of consecutive text/list-item blocks into chunks near
        the target token size, keeping blocks together where they fit."""
        if not blocks:
            return []
        texts = [f"- {block}" if is_list else block for block in blocks]
        return self._splitter.split_text("\n\n".join(texts))

    def split_table(self, header: list[str], rows: list[list[str]]) -> list[str]:
        """Split a Markdown table without ever breaking a row.

        The header row is repeated in every output chunk so each one remains
        a valid, standalone Markdown table.
        """
        header_tokens = count_tokens(" ".join(header))
        chunks: list[str] = []
        buffer: list[list[str]] = []
        buffer_tokens = header_tokens

        for row in rows:
            row_tokens = count_tokens(" ".join(row))
            if buffer and buffer_tokens + row_tokens > self._target_tokens:
                chunks.append(self.render_table(header, buffer))
                buffer = []
                buffer_tokens = header_tokens
            buffer.append(row)
            buffer_tokens += row_tokens

        if buffer:
            chunks.append(self.render_table(header, buffer))

        return chunks

    @staticmethod
    def render_table(header: list[str], rows: list[list[str]]) -> str:
        """Render a GitHub-Flavored Markdown table."""
        lines = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join("---" for _ in header) + " |",
        ]
        lines.extend("| " + " | ".join(row) + " |" for row in rows)
        return "\n".join(lines)
