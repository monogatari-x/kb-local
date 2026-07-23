from kb_core.chunkers.recursive_chunker import RecursiveChunker
from kb_core.enums import ChunkType
from kb_core.loaders.base import Block, LoadedDocument


def test_short_block_single_chunk():
    block = Block(text="hello world", start_line=1, end_line=1, kind="paragraph")
    loaded = LoadedDocument(text="hello world", language=None, blocks=[block], meta={})
    chunks = RecursiveChunker(max_tokens=100, overlap=0).chunk(loaded)
    assert len(chunks) == 1
    assert chunks[0].chunk_type == ChunkType.PARAGRAPH
    assert chunks[0].tokens > 0
    assert chunks[0].content_hash
    assert chunks[0].ordinal == 0


def test_long_block_splits():
    text = "这是一个句子。".replace("。", "。 ") * 200
    block = Block(text=text, start_line=1, end_line=10, kind="paragraph")
    loaded = LoadedDocument(text=text, language=None, blocks=[block], meta={})
    chunks = RecursiveChunker(max_tokens=50, overlap=5).chunk(loaded)
    assert len(chunks) > 1
    for c in chunks:
        assert c.tokens <= 100


def test_multi_block_preserves_line_numbers():
    b1 = Block(text="aaa", start_line=1, end_line=1, kind="paragraph")
    b2 = Block(text="bbb", start_line=3, end_line=3, kind="paragraph")
    loaded = LoadedDocument(text="aaa\n\nbbb", language=None, blocks=[b1, b2], meta={})
    chunks = RecursiveChunker(max_tokens=100, overlap=0).chunk(loaded)
    assert chunks[0].start_line == 1
    assert chunks[1].start_line == 3


def test_chunk_ids_unique():
    block = Block(text="x. y. z.", start_line=1, end_line=1, kind="paragraph")
    loaded = LoadedDocument(text="x. y. z.", language=None, blocks=[block], meta={})
    chunks = RecursiveChunker(max_tokens=3, overlap=0).chunk(loaded)
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))
