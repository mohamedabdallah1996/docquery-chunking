"""Internal representation used while chunking a document.

These are plain dataclasses, not docquery_core types -- they never cross the
package boundary. Only `chunker.py`'s return value (`list[Chunk]`) does.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

BlockKind = Literal["heading", "text", "list_item", "table", "code"]


@dataclass(slots=True, frozen=True)
class MarkdownBlock:
    """One logical Markdown block extracted from a ParsedPage."""

    kind: BlockKind
    page: int
    text: str = ""

    # heading only
    level: int | None = None

    # table only
    table_header: list[str] | None = None
    table_rows: list[list[str]] | None = None


@dataclass(slots=True)
class DocumentSection:
    """A document section identified by its heading hierarchy.

    Example: "Introduction" > "Background" becomes ["Introduction", "Background"].
    """

    path: list[str]
    blocks: list[MarkdownBlock] = field(default_factory=list)
