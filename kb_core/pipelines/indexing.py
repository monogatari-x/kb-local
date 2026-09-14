import uuid
from datetime import datetime
from pathlib import Path

from kb_core.chunkers.base import BaseChunker
from kb_core.config import ChunkingConfig
from kb_core.embeddings.bge_m3 import BGE_M3_EMBEDDER
from kb_core.enums import DocStatus, FileType, ProjectStrategy
from kb_core.exceptions import KBError
from kb_core.loaders.registry import LoaderRegistry
from kb_core.models import Document
from kb_core.stores.qdrant_store import QdrantStore
from kb_core.stores.sqlite_store import SQLiteStore
from kb_core.utils.hashing import sha256_of_file
from kb_core.utils.paths import infer_project, rel_path

_EXT_TO_FILETYPE = {
    ".php": FileType.CODE,
    ".py": FileType.CODE,
    ".java": FileType.CODE,
    ".js": FileType.CODE,
    ".ts": FileType.CODE,
    ".go": FileType.CODE,
    ".md": FileType.MARKDOWN,
    ".markdown": FileType.MARKDOWN,
    ".txt": FileType.TEXT,
    ".log": FileType.TEXT,
    ".pdf": FileType.TEXT,
    ".docx": FileType.TEXT,
    ".xlsx": FileType.TEXT,
    ".xls": FileType.TEXT,
}

PARSER_VERSION = "0.2.0"


class IndexingPipeline:
    def __init__(
        self,
        sqlite_store: SQLiteStore,
        qdrant_store: QdrantStore,
        registry: LoaderRegistry,
        embedder: BGE_M3_EMBEDDER,
        chunkers: dict[str, BaseChunker],
        chunking_config: ChunkingConfig | None = None,
    ) -> None:
        self.sqlite_store = sqlite_store
        self.qdrant_store = qdrant_store
        self.registry = registry
        self.embedder = embedder
        self.chunkers = chunkers
        self.chunking_config = chunking_config or ChunkingConfig()

    def index_file(
        self,
        path: Path,
        watch_dir: Path,
        project_strategy: str,
        project_name: str,
    ) -> str:
        ext = path.suffix.lower()
        loader = self.registry.get_for_extension(ext)
        if loader is None:
            raise KBError(f"No loader for {ext}")
        file_type = _EXT_TO_FILETYPE.get(ext, FileType.TEXT)
        sha = sha256_of_file(path)
        existing = self.sqlite_store.get_document_by_path(str(path))

        if (
            existing is not None
            and existing.sha256 == sha
            and existing.status == DocStatus.ACTIVE
            and existing.parser_version == PARSER_VERSION
        ):
            return existing.doc_id

        loaded = loader.load(path)
        chunker_key = (
            "code"
            if file_type == FileType.CODE
            else ("markdown" if file_type == FileType.MARKDOWN else "text")
        )
        chunker = self.chunkers[chunker_key]
        raw_chunks = chunker.chunk(loaded)

        doc_id = str(uuid.uuid5(uuid.NAMESPACE_OID, str(path)))

        if existing is not None:
            self.sqlite_store.delete_chunks_of_doc(doc_id)
            self.qdrant_store.delete_by_doc(doc_id)

        doc = Document(
            doc_id=doc_id,
            source_path=str(path),
            rel_path=rel_path(path, watch_dir),
            project=infer_project(path, watch_dir, ProjectStrategy(project_strategy), project_name),
            file_type=file_type,
            language=loaded.language,
            sha256=sha,
            size_bytes=path.stat().st_size,
            mtime=datetime.fromtimestamp(path.stat().st_mtime),
            ingested_at=datetime.now(),
            indexed_at=datetime.now(),
            embedding_version=getattr(self.embedder, "model_name", "unknown"),
            parser_version=PARSER_VERSION,
        )
        for c in raw_chunks:
            c.doc_id = doc_id
            c.meta = {
                "project": doc.project,
                "tags": doc.tags,
                "embedding_version": doc.embedding_version,
            }

        if raw_chunks:
            dense, sparse = self.embedder.embed_texts([c.text for c in raw_chunks])
            self.qdrant_store.upsert_chunks(raw_chunks, dense, sparse)

        self.sqlite_store.upsert_document(doc)
        if raw_chunks:
            self.sqlite_store.upsert_chunks(raw_chunks)
        return doc_id

    def remove_document(self, doc_id: str) -> None:
        self.sqlite_store.delete_chunks_of_doc(doc_id)
        self.sqlite_store.conn.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
        self.qdrant_store.delete_by_doc(doc_id)
