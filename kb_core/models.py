from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from kb_core.enums import ChunkType, DocStatus, FileType


TRUNCATE_LEN = 500


class Document(BaseModel):
    doc_id: str
    source_path: str
    rel_path: str
    project: str
    file_type: FileType
    language: str | None = None
    sha256: str
    size_bytes: int
    mtime: datetime
    ingested_at: datetime
    indexed_at: datetime | None = None
    embedding_version: str | None = None
    parser_version: str | None = None
    tags: list[str] = Field(default_factory=list)
    status: DocStatus = DocStatus.ACTIVE
    error_msg: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class Chunk(BaseModel):
    chunk_id: str
    doc_id: str
    ordinal: int
    text: str
    text_truncated: str | None = None
    tokens: int
    content_hash: str
    start_char: int
    end_char: int
    start_line: int | None = None
    end_line: int | None = None
    section_path: str | None = None
    symbol_path: str | None = None
    chunk_type: ChunkType
    quality_score: float
    language: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _auto_truncate(self) -> "Chunk":
        if self.text_truncated is None:
            self.text_truncated = self.text[:TRUNCATE_LEN]
        return self


class SearchResult(BaseModel):
    chunk: Chunk
    document: Document | None
    final_score: float
    vector_score: float
    rerank_score: float = 0.0
    citation: str
    highlights: list[str] = Field(default_factory=list)
    prev_chunk_id: str | None = None
    next_chunk_id: str | None = None
