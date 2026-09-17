# docquery-chunking

> `ParsedDocument` -> `list[Chunk]`. One of DocQuery's independently versioned pipeline submodules.

## Overview

Takes a [`docquery_core.ParsedDocument`](https://github.com/mohamedabdallah1996/docquery-core)
(ingestion's output) and splits it into header-aware, retrieval-sized
[`docquery_core.Chunk`](https://github.com/mohamedabdallah1996/docquery-core) objects, ready for
embedding. No submodule-to-submodule calls: this package takes input, produces output, nothing
more.

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12+ |
| Markdown parsing | markdown-it-py (+ GFM plugin, for tables) |
| Text splitting | langchain-text-splitters |
| Token counting | tiktoken |
| Data contracts | docquery-core (pydantic) |
| Package/dependency management | uv |
| Linting & formatting | Ruff |
| Type checking | mypy (`--strict`) |
| Testing | pytest |

## Architecture

A four-stage pipeline, each stage owning one concern:

1. **`MarkdownParser`** parses each page's markdown into a flat, typed sequence of
   `MarkdownBlock`s (heading, text, list item, table, code) using markdown-it-py's real
   CommonMark+GFM parser -- not regexes -- so table rows and code fences are recognized
   structurally instead of guessed at from raw text.
2. **`SectionBuilder`** groups blocks under the document's heading hierarchy (a `##` closes out
   any deeper heading that came before it) and merges sections that are too small to be
   useful on their own into the section that follows -- except sections containing a table,
   which are never merged away regardless of size.
3. **`SectionChunker`** walks each section in order, accumulating consecutive text/list blocks
   into a run (split together, see below) while emitting tables and code blocks as their own
   standalone chunk(s) immediately.
4. **`TextSplitter`** turns an accumulated text/list run into one or more chunks near
   `target_tokens`, and splits an oversized table by row group. Text splitting delegates to
   LangChain's `RecursiveCharacterTextSplitter` (paragraph -> line -> sentence -> word/character,
   recursively, measured against a real tokenizer) rather than a hand-rolled version -- that
   problem is already solved well elsewhere. Table splitting stays custom: a row is atomic in a
   way no generic text splitter understands, and the header must be repeated in every split-off
   piece to remain valid Markdown.

`StructureAwareChunker` (`chunker.py`) is the only concrete strategy today -- one concrete class,
no strategy hierarchy, matching `docquery-ingestion`'s precedent of not introducing a
Protocol/base class until a second real implementation exists to justify one.

`build_chunker()` (`factory.py`) is the one place "which strategy" gets decided from a raw config
dict -- callers never construct `StructureAwareChunker` directly.

Token counting (`utils.count_tokens`) uses a generic tiktoken encoding, deliberately *not* the
embedding model's actual tokenizer -- chunking doesn't know, and shouldn't need to know, which
embedder will consume its output. `target_tokens` is a soft sizing target for retrieval quality,
not a hard limit any API enforces, so an approximate, model-agnostic count is the right amount of
precision here.

## Project Structure

```
src/docquery_chunking/
  chunker.py                 # StructureAwareChunker -- the only concrete strategy today
  config.py                     # ChunkingConfig
  factory.py                       # build_chunker() -- resolves config -> a ready chunker
  models.py                          # MarkdownBlock, DocumentSection (internal, not exchanged)
  utils.py                              # count_tokens, stable_id
  components/
    markdown_parser.py                    # ParsedDocument -> MarkdownBlocks
    section_builder.py                       # MarkdownBlocks -> DocumentSections
    section_chunker.py                          # DocumentSection -> Chunks
    text_splitter.py                               # size-bounded text/table splitting
tests/                                               # end-to-end behavioral tests
```

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

### Installation

```bash
git clone https://github.com/mohamedabdallah1996/docquery-chunking
cd docquery-chunking
uv sync
```

### Using it

```python
from docquery_chunking import build_chunker

chunker = build_chunker({"chunking": {"target_tokens": 500, "min_section_tokens": 30}})
chunks = chunker.chunk(parsed_document)
```

`docquery-core` is depended on via a git source (`[tool.uv.sources]`), not a local path -- this
package's own checkout has no sibling `docquery-core` directory to point a path at. The
orchestrator overrides this the same way for its own reasons; see
[`docquery`'s README](https://github.com/mohamedabdallah1996/DocQuery) for that side of it.

## Testing

```bash
uv run pytest
```

## Development

```bash
uv run ruff check .
uv run ruff format .
uv run mypy src
```
