from pathlib import Path

from kb_core.chunkers.markdown_chunker import MarkdownChunker
from kb_core.enums import ChunkType
from kb_core.loaders.base import Block, LoadedDocument
from kb_core.loaders.markdown_loader import MarkdownLoader


def test_heading_chunk():
    block = Block(
        text="", start_line=1, end_line=1, kind="heading", extra={"level": 2, "title": "Sub Title"}
    )
    loaded = LoadedDocument(text="# X\n## Sub Title", language="markdown", blocks=[block], meta={})
    chunks = MarkdownChunker().chunk(loaded)
    assert any(c.chunk_type == ChunkType.HEADING for c in chunks)
    heading = next(c for c in chunks if c.chunk_type == ChunkType.HEADING)
    assert heading.section_path == "Sub Title"


def test_code_block_intact():
    code = "def f():\n    return 1\n"
    block = Block(
        text=code, start_line=3, end_line=5, kind="code_block", extra={"language": "python"}
    )
    loaded = LoadedDocument(text=code, language="markdown", blocks=[block], meta={})
    chunks = MarkdownChunker().chunk(loaded)
    assert len(chunks) == 1
    assert chunks[0].text == code
    assert chunks[0].language == "python"


def test_paragraph_delegates_recursive():
    block = Block(text="one two three", start_line=1, end_line=1, kind="paragraph")
    loaded = LoadedDocument(text="one two three", language="markdown", blocks=[block], meta={})
    chunks = MarkdownChunker().chunk(loaded)
    assert len(chunks) >= 1
    assert chunks[0].chunk_type == ChunkType.PARAGRAPH


def test_end_to_end_plain_note_produces_chunks(tmp_path: Path):
    note = tmp_path / "note.md"
    note.write_text(
        "一、投诉匿名化需求要点\r\n二、响应分级提醒机制\r\n", encoding="utf-8", newline=""
    )
    chunks = MarkdownChunker().chunk(MarkdownLoader().load(note))
    assert chunks
    assert any(c.chunk_type == ChunkType.PARAGRAPH for c in chunks)
    assert any("匿名化" in c.text for c in chunks)


def test_end_to_end_body_text_indexed(tmp_path: Path):
    doc_file = tmp_path / "guide.md"
    doc_file.write_text(
        "# 手册标题\n\n正文第一段的重要关键词镧系元素。\n\n## 小节\n\n正文第二段。\n",
        encoding="utf-8",
    )
    chunks = MarkdownChunker().chunk(MarkdownLoader().load(doc_file))
    assert any("镧系元素" in c.text for c in chunks)
