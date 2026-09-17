"""Splits text/list runs and oversized tables into retrieval-sized chunks.

Text splitting delegates to LangChain's RecursiveCharacterTextSplitter
(paragraph -> line -> sentence -> word/char, tokenizer-aware) rather than a
hand-rolled version. Table splitting stays custom: a row is atomic, and the
header must repeat in every split-off piece to stay valid Markdown.
"""

from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter

from docquery_chunking.utils import count_tokens

# Largest-to-smallest split points, tried in order.
_SEPARATORS = ["\n\n", "\n", ". ", "! ", "? ", " ", ""]


class TextSplitter:
    def __init__(self, *, target_tokens: int, min_section_tokens: int) -> None:
        self._target_tokens = target_tokens
        self._min_section_tokens = min_section_tokens
        self._splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            encoding_name="cl100k_base",
            separators=_SEPARATORS,
            chunk_size=target_tokens,
            chunk_overlap=0,
            keep_separator="end",
        )

    def split_text_blocks(self, blocks: list[str], *, is_list: bool = False) -> list[str]:
        """Split a run of consecutive text/list-item blocks into chunks near
        the target token size, keeping blocks together where they fit."""
        if not blocks:
            return []
        texts = [f"- {block}" if is_list else block for block in blocks]
        pieces = self._splitter.split_text("\n\n".join(texts))
        return self._merge_undersized_pieces(pieces)

    def _merge_undersized_pieces(self, pieces: list[str]) -> list[str]:
        """Fold an undersized piece into the one that follows it, if it fits.

        Edge case: an undersized *last* piece has nothing to fold into and
        is left as-is (e.g. a short remark trailing an oversized paragraph).
        """
        if not pieces:
            return pieces

        merged = [pieces[0]]
        for piece in pieces[1:]:
            fits_budget = count_tokens(merged[-1]) + count_tokens(piece) <= self._target_tokens
            if count_tokens(merged[-1]) < self._min_section_tokens and fits_budget:
                merged[-1] = f"{merged[-1]}\n\n{piece}"
            else:
                merged.append(piece)
        return merged

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
