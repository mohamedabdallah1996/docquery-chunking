from docquery_chunking.chunker import StructureAwareChunker
from docquery_chunking.factory import build_chunker


def test_build_chunker_resolves_config_into_a_ready_chunker() -> None:
    chunker = build_chunker({"chunking": {"target_tokens": 250}})
    assert isinstance(chunker, StructureAwareChunker)
