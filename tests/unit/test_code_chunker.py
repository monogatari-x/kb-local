from kb_core.chunkers.code_chunker import CodeChunker
from kb_core.enums import ChunkType
from kb_core.loaders.base import Block, LoadedDocument


def test_function_chunk():
    block = Block(text="def f():\n    return 1\n", start_line=1, end_line=3,
                  kind="code_function", extra={"symbol": "f"})
    loaded = LoadedDocument(text=block.text, language="python", blocks=[block], meta={})
    chunks = CodeChunker().chunk(loaded)
    assert len(chunks) == 1
    assert chunks[0].chunk_type == ChunkType.CODE_FUNCTION
    assert chunks[0].symbol_path == "f"
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 3


def test_class_chunk():
    block = Block(text="class A:\n    pass\n", start_line=1, end_line=2,
                  kind="code_class", extra={"symbol": "A"})
    loaded = LoadedDocument(text=block.text, language="python", blocks=[block], meta={})
    chunks = CodeChunker().chunk(loaded)
    assert len(chunks) == 1
    assert chunks[0].chunk_type == ChunkType.CODE_CLASS
    assert chunks[0].symbol_path == "A"


def test_oversized_function_splits():
    long_body = "    x = " + "1 + " * 500 + "1\n"
    block = Block(text=f"def big():\n{long_body}", start_line=1, end_line=10,
                  kind="code_function", extra={"symbol": "big"})
    loaded = LoadedDocument(text=block.text, language="python", blocks=[block], meta={})
    chunks = CodeChunker(max_tokens=50).chunk(loaded)
    assert len(chunks) > 1
    assert chunks[0].chunk_type == ChunkType.CODE_FUNCTION
