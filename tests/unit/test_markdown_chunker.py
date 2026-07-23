from kb_core.chunkers.markdown_chunker import MarkdownChunker
from kb_core.enums import ChunkType
from kb_core.loaders.base import Block, LoadedDocument


def test_heading_chunk():
    block = Block(text="", start_line=1, end_line=1, kind="heading",
                  extra={"level": 2, "title": "Sub Title"})
    loaded = LoadedDocument(text="# X\n## Sub Title", language="markdown",
                            blocks=[block], meta={})
    chunks = MarkdownChunker().chunk(loaded)
    assert any(c.chunk_type == ChunkType.HEADING for c in chunks)
    heading = next(c for c in chunks if c.chunk_type == ChunkType.HEADING)
    assert heading.section_path == "Sub Title"


def test_code_block_intact():
    code = "def f():\n    return 1\n"
    block = Block(text=code, start_line=3, end_line=5, kind="code_block",
                  extra={"language": "python"})
    loaded = LoadedDocument(text=code, language="markdown", blocks=[block], meta={})
    chunks = MarkdownChunker().chunk(loaded)
    assert len(chunks) == 1
    assert chunks[0].text == code
    assert chunks[0].language == "python"


def test_paragraph_delegates_recursive():
    block = Block(text="one two three", start_line=1, end_line=1, kind="paragraph")
    loaded = LoadedDocument(text="one two three", language="markdown",
                            blocks=[block], meta={})
    chunks = MarkdownChunker().chunk(loaded)
    assert len(chunks) >= 1
    assert chunks[0].chunk_type == ChunkType.PARAGRAPH
