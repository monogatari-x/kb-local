from datetime import datetime

from kb_core.enums import ChunkType, DocStatus, FileType, ProjectStrategy
from kb_core.models import Chunk, Document, SearchResult


def test_document_minimal():
    doc = Document(
        doc_id="d-1",
        source_path="C:/Glow/projects/yaf/src/Login.php",
        rel_path="yaf/src/Login.php",
        project="yaf",
        file_type=FileType.CODE,
        language="php",
        sha256="abc123",
        size_bytes=1024,
        mtime=datetime(2026, 7, 22, 10, 0, 0),
        ingested_at=datetime(2026, 7, 22, 10, 0, 1),
        embedding_version="bge-m3-v1",
        parser_version="tree-sitter-0.22",
    )
    assert doc.status == DocStatus.ACTIVE
    assert doc.tags == []
    assert doc.meta == {}


def test_chunk_with_line_numbers():
    chunk = Chunk(
        chunk_id="c-1",
        doc_id="d-1",
        ordinal=0,
        text="def hello():\n    pass",
        tokens=10,
        content_hash="def-hash",
        start_char=0,
        end_char=20,
        start_line=1,
        end_line=2,
        chunk_type=ChunkType.CODE_FUNCTION,
        quality_score=1.0,
    )
    assert chunk.language is None
    assert chunk.section_path is None


def test_chunk_truncated_auto_filled():
    long_text = "x" * 1000
    chunk = Chunk(
        chunk_id="c-2",
        doc_id="d-1",
        ordinal=0,
        text=long_text,
        tokens=500,
        content_hash="hash",
        start_char=0,
        end_char=1000,
        chunk_type=ChunkType.PARAGRAPH,
        quality_score=0.8,
    )
    assert len(chunk.text_truncated) == 500
    assert chunk.text_truncated.startswith("xxxxx")


def test_project_strategy_values():
    assert ProjectStrategy.FIXED.value == "fixed"
    assert ProjectStrategy.FIRST_SUBDIR.value == "first_subdir"


def test_search_result_citation_field():
    sr = SearchResult(
        chunk=Chunk(
            chunk_id="c-1", doc_id="d-1", ordinal=0, text="hi",
            tokens=1, content_hash="h", start_char=0, end_char=2,
            chunk_type=ChunkType.PARAGRAPH, quality_score=1.0,
        ),
        document=None,  # 允许 None，便于测试
        final_score=0.9,
        vector_score=0.85,
        rerank_score=0.0,
        citation="yaf/src/Login.php:1-2",
        highlights=["hi"],
    )
    assert sr.prev_chunk_id is None
