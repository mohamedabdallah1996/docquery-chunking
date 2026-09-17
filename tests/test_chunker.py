from docquery_core import Chunk, ParsedDocument, ParsedPage

from docquery_chunking.chunker import StructureAwareChunker
from docquery_chunking.config import ChunkingConfig
from docquery_chunking.utils import count_tokens

_CONFIG = ChunkingConfig()

# A single-section prefix shared by tests that don't care about section structure.
SECTION = "# Title\n\n## Section\n\n"

# Comfortably over min_section_tokens, so a section built from this is never a
# small-section merge candidate.
SUBSTANTIAL = (
    "This paragraph has plenty of words in it so that it clearly and safely "
    "exceeds the small-section merge threshold all on its own, with a bit "
    "more padding besides. "
)


def _doc(markdown: str) -> ParsedDocument:
    """Wrap a single page of markdown in a minimal ParsedDocument."""
    page = ParsedPage(page_number=1, markdown=markdown)
    return ParsedDocument(doc_id="doc1", pages=(page,), status="DONE")


def _chunk(markdown: str) -> list[Chunk]:
    """Run the structure-aware chunker over a single page of markdown."""
    return StructureAwareChunker(_CONFIG).chunk(_doc(markdown))


def test_headers_define_section_path() -> None:
    """Each header opens a new section, tagging its chunks with that breadcrumb."""
    chunks = _chunk(f"# Title\n\n## Section A\n\n{SUBSTANTIAL}\n\n## Section B\n\n{SUBSTANTIAL}\n")
    paths = {c.section_path for c in chunks}
    assert ("Title", "Section A") in paths
    assert ("Title", "Section B") in paths


def test_nested_headers_pop_back_to_correct_level() -> None:
    """A shallower header (##) closes out a deeper one (###) that came before it."""
    chunks = _chunk(f"# Title\n\n## A\n\n### A1\n\n{SUBSTANTIAL}\n\n## B\n\n{SUBSTANTIAL}\n")
    paths = {c.section_path for c in chunks}
    assert ("Title", "A", "A1") in paths
    assert ("Title", "B") in paths  # sibling of A, not nested under A1


def test_table_is_atomic_and_rows_stay_intact() -> None:
    """A table becomes one chunk; rows are never split mid-table."""
    chunks = _chunk(f"{SECTION}| Col A | Col B |\n| --- | --- |\n| 1 | 2 |\n| 3 | 4 |\n")
    tables = [c for c in chunks if c.chunk_type == "table"]
    assert len(tables) == 1
    assert "| 1 | 2 |" in tables[0].content
    assert "| 3 | 4 |" in tables[0].content


def test_large_table_splits_by_row_group_with_header_repeated() -> None:
    """An oversized table splits by row-group, repeating the header in each part."""
    rows = "\n".join(f"| {i} | {i * 2} |" for i in range(300))
    chunks = _chunk(f"{SECTION}| Col A | Col B |\n| --- | --- |\n{rows}\n")
    tables = [c for c in chunks if c.chunk_type == "table"]
    assert len(tables) > 1
    for table in tables:
        assert table.content.startswith("| Col A | Col B |")


def test_fenced_code_block_becomes_its_own_atomic_chunk() -> None:
    """A code fence is never dropped or folded into surrounding text."""
    markdown = f"{SECTION}```python\nprint('hello')\n```\n\n{SUBSTANTIAL}\n"
    chunks = _chunk(markdown)
    code_chunks = [c for c in chunks if c.chunk_type == "code"]
    assert len(code_chunks) == 1
    assert code_chunks[0].content == "print('hello')\n"
    assert not any("print('hello')" in c.content for c in chunks if c.chunk_type != "code")


def test_list_items_produce_list_chunk_type() -> None:
    """A chunk made up entirely of list items is tagged chunk_type='list'."""
    markdown = (
        f"{SECTION}- item one padded with words\n"
        "- item two padded with words\n"
        "- item three padded with words\n"
    )
    chunks = _chunk(markdown)
    lists = [c for c in chunks if c.chunk_type == "list"]
    assert len(lists) == 1
    assert "item one" in lists[0].content
    assert "item three" in lists[0].content


def test_small_section_merges_forward_into_next() -> None:
    """A bare header + one short line merges into the next section instead of
    standing alone -- but its own heading is preserved in the merged path,
    not silently dropped, so a citation doesn't point at the wrong section."""
    chunks = _chunk(f"# Title\n\n## Empty\n\nx\n\n## Next\n\n{SUBSTANTIAL}\n")
    paths = {c.section_path for c in chunks}
    assert ("Title", "Empty") not in paths
    merged_chunks = [c for c in chunks if c.section_path == ("Title", "Empty / Next")]
    assert any(c.content.startswith("x") for c in merged_chunks)


def test_section_with_table_is_never_merged_away_even_if_small() -> None:
    """A table makes a section substantive regardless of word count, so it never merges away."""
    markdown = (
        "# Title\n\n## HasTable\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n\n"
        f"## Next\n\n{SUBSTANTIAL}\n"
    )
    chunks = _chunk(markdown)
    table_chunks = [c for c in chunks if c.chunk_type == "table"]
    assert len(table_chunks) == 1
    assert table_chunks[0].section_path == ("Title", "HasTable")


def test_oversized_paragraph_splits_and_stays_within_budget() -> None:
    """A single paragraph too big to fit in one chunk gets split into several,
    each still within the configured token budget."""
    long_paragraph = " ".join(f"This is sentence number {i}." for i in range(150))
    chunks = _chunk(f"{SECTION}{long_paragraph}\n")
    text_chunks = [c for c in chunks if c.chunk_type == "text"]
    assert len(text_chunks) > 1
    assert "sentence number 0." in text_chunks[0].content
    assert "sentence number 149." in text_chunks[-1].content
    for c in text_chunks:
        assert count_tokens(c.content) <= _CONFIG.target_tokens


def test_chunking_is_deterministic() -> None:
    """Chunking the same document twice produces identical chunk and parent IDs."""
    doc = _doc(f"{SECTION}Some stable content that will always chunk the same way.\n")
    chunker = StructureAwareChunker(_CONFIG)
    first = chunker.chunk(doc)
    second = chunker.chunk(doc)
    assert [c.chunk_id for c in first] == [c.chunk_id for c in second]
    assert [c.parent_chunk_id for c in first] == [c.parent_chunk_id for c in second]
