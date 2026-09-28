import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from kb_core.enums import ChunkType, DocStatus, FileType
from kb_core.exceptions import SQLiteError
from kb_core.models import Chunk, Document

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


class SQLiteStore:
    def __init__(self, db_path: Path, check_same_thread: bool = False):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.conn = sqlite3.connect(
                db_path, isolation_level=None, check_same_thread=check_same_thread
            )
            self.conn.execute("PRAGMA foreign_keys = ON")
            self.conn.execute("PRAGMA journal_mode = WAL")
            self.conn.execute("PRAGMA busy_timeout = 5000")
            self.conn.row_factory = sqlite3.Row
        except sqlite3.Error as e:
            raise SQLiteError(f"Cannot open {db_path}: {e}") from e

    def init_schema(self) -> None:
        try:
            self.conn.executescript(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "  name TEXT PRIMARY KEY, applied_at TEXT NOT NULL"
                ");"
            )
            applied = {
                row["name"]
                for row in self.conn.execute("SELECT name FROM schema_migrations").fetchall()
            }
            for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
                if sql_file.name in applied:
                    continue
                self.conn.executescript(sql_file.read_text(encoding="utf-8"))
                self.conn.execute(
                    "INSERT INTO schema_migrations(name, applied_at) VALUES (?, ?)",
                    (sql_file.name, self._iso(datetime.now())),
                )
        except sqlite3.Error as e:
            raise SQLiteError(f"Migration failed: {e}") from e

    def close(self) -> None:
        self.conn.close()

    def _iso(self, dt: datetime | None) -> str | None:
        return dt.isoformat() if dt else None

    def _parse_iso(self, s: str | None) -> datetime | None:
        return datetime.fromisoformat(s) if s else None

    def upsert_document(self, doc: Document) -> None:
        try:
            self.conn.execute(
                """INSERT INTO documents(doc_id, source_path, rel_path, project, author, file_type,
                       language, sha256, size_bytes, mtime, ingested_at, indexed_at,
                       embedding_version, parser_version, status, error_msg, tags, meta)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(doc_id) DO UPDATE SET
                       source_path=excluded.source_path, rel_path=excluded.rel_path,
                       project=excluded.project, author=excluded.author,
                       file_type=excluded.file_type,
                       language=excluded.language, sha256=excluded.sha256,
                       size_bytes=excluded.size_bytes, mtime=excluded.mtime,
                       ingested_at=excluded.ingested_at, indexed_at=excluded.indexed_at,
                       embedding_version=excluded.embedding_version,
                       parser_version=excluded.parser_version, status=excluded.status,
                       error_msg=excluded.error_msg, tags=excluded.tags, meta=excluded.meta""",
                (
                    doc.doc_id,
                    doc.source_path,
                    doc.rel_path,
                    doc.project,
                    doc.author,
                    doc.file_type.value,
                    doc.language,
                    doc.sha256,
                    doc.size_bytes,
                    self._iso(doc.mtime),
                    self._iso(doc.ingested_at),
                    self._iso(doc.indexed_at),
                    doc.embedding_version,
                    doc.parser_version,
                    doc.status.value,
                    doc.error_msg,
                    json.dumps(doc.tags),
                    json.dumps(doc.meta),
                ),
            )
        except sqlite3.Error as e:
            raise SQLiteError(f"upsert_document failed: {e}") from e

    def _row_to_doc(self, row: sqlite3.Row) -> Document:
        mtime = self._parse_iso(row["mtime"])
        ingested_at = self._parse_iso(row["ingested_at"])
        assert mtime is not None and ingested_at is not None
        return Document(
            doc_id=row["doc_id"],
            source_path=row["source_path"],
            rel_path=row["rel_path"],
            project=row["project"],
            author=row["author"],
            file_type=FileType(row["file_type"]),
            language=row["language"],
            sha256=row["sha256"],
            size_bytes=row["size_bytes"],
            mtime=mtime,
            ingested_at=ingested_at,
            indexed_at=self._parse_iso(row["indexed_at"]),
            embedding_version=row["embedding_version"],
            parser_version=row["parser_version"],
            status=DocStatus(row["status"]),
            error_msg=row["error_msg"],
            tags=json.loads(row["tags"] or "[]"),
            meta=json.loads(row["meta"] or "{}"),
        )

    def get_document(self, doc_id: str) -> Document | None:
        row = self.conn.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()
        return self._row_to_doc(row) if row else None

    def get_document_by_path(self, source_path: str) -> Document | None:
        row = self.conn.execute(
            "SELECT * FROM documents WHERE source_path = ?", (source_path,)
        ).fetchone()
        return self._row_to_doc(row) if row else None

    def delete_chunks_of_doc(self, doc_id: str) -> int:
        cur = self.conn.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
        return cur.rowcount

    def mark_document_deleted(self, doc_id: str) -> None:
        self.conn.execute(
            "UPDATE documents SET status = ? WHERE doc_id = ?",
            (DocStatus.DELETED.value, doc_id),
        )

    def upsert_chunks(self, chunks: list[Chunk]) -> None:
        for c in chunks:
            self.conn.execute(
                """INSERT INTO chunks(chunk_id, doc_id, ordinal, text, text_truncated, tokens,
                       content_hash, start_char, end_char, start_line, end_line,
                       section_path, symbol_path, chunk_type, quality_score, language, meta)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(chunk_id) DO UPDATE SET
                       text=excluded.text, tokens=excluded.tokens,
                       content_hash=excluded.content_hash""",
                (
                    c.chunk_id,
                    c.doc_id,
                    c.ordinal,
                    c.text,
                    c.text_truncated,
                    c.tokens,
                    c.content_hash,
                    c.start_char,
                    c.end_char,
                    c.start_line,
                    c.end_line,
                    c.section_path,
                    c.symbol_path,
                    c.chunk_type.value,
                    c.quality_score,
                    c.language,
                    json.dumps(c.meta),
                ),
            )

    def _row_to_chunk(self, row: sqlite3.Row) -> Chunk:
        return Chunk(
            chunk_id=row["chunk_id"],
            doc_id=row["doc_id"],
            ordinal=row["ordinal"],
            text=row["text"],
            text_truncated=row["text_truncated"],
            tokens=row["tokens"],
            content_hash=row["content_hash"],
            start_char=row["start_char"],
            end_char=row["end_char"],
            start_line=row["start_line"],
            end_line=row["end_line"],
            section_path=row["section_path"],
            symbol_path=row["symbol_path"],
            chunk_type=ChunkType(row["chunk_type"]),
            quality_score=row["quality_score"],
            language=row["language"],
            meta=json.loads(row["meta"] or "{}"),
        )

    def get_chunk(self, chunk_id: str) -> Chunk | None:
        row = self.conn.execute("SELECT * FROM chunks WHERE chunk_id = ?", (chunk_id,)).fetchone()
        return self._row_to_chunk(row) if row else None

    def get_chunks_by_doc(self, doc_id: str) -> list[Chunk]:
        rows = self.conn.execute(
            "SELECT * FROM chunks WHERE doc_id = ? ORDER BY ordinal", (doc_id,)
        ).fetchall()
        return [self._row_to_chunk(r) for r in rows]

    def get_neighbor_chunk_ids(self, chunk_id: str) -> tuple[str | None, str | None]:
        row = self.conn.execute(
            "SELECT doc_id, ordinal FROM chunks WHERE chunk_id = ?", (chunk_id,)
        ).fetchone()
        if row is None:
            return (None, None)
        prev_row = self.conn.execute(
            "SELECT chunk_id FROM chunks WHERE doc_id = ? AND ordinal = ?",
            (row["doc_id"], row["ordinal"] - 1),
        ).fetchone()
        next_row = self.conn.execute(
            "SELECT chunk_id FROM chunks WHERE doc_id = ? AND ordinal = ?",
            (row["doc_id"], row["ordinal"] + 1),
        ).fetchone()
        return (
            prev_row["chunk_id"] if prev_row else None,
            next_row["chunk_id"] if next_row else None,
        )

    def add_watch_dir(
        self,
        path: str,
        project_name: str,
        strategy: str,
        recursive: bool,
        exclude_patterns: list[str],
        file_types: list[str] | None = None,
        include_patterns: list[str] | None = None,
        author: str = "",
    ) -> int:
        cur = self.conn.execute(
            """INSERT INTO watch_dirs(path, project_name, project_strategy, recursive,
                   file_types, include_patterns, exclude_patterns, created_at, author)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                path,
                project_name,
                strategy,
                int(recursive),
                json.dumps(file_types or []),
                json.dumps(include_patterns or []),
                json.dumps(exclude_patterns),
                self._iso(datetime.now()),
                author,
            ),
        )
        watch_id = cur.lastrowid
        assert watch_id is not None
        return watch_id

    def list_watch_dirs(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM watch_dirs ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    def remove_watch_dir(self, watch_id: int) -> None:
        self.conn.execute("DELETE FROM watch_dirs WHERE id = ?", (watch_id,))

    def create_job(self, type_: str, trigger: str) -> str:
        job_id = str(uuid.uuid4())
        self.conn.execute(
            """INSERT INTO jobs(job_id, type, status, started_at, trigger)
               VALUES (?, ?, 'running', ?, ?)""",
            (job_id, type_, self._iso(datetime.now()), trigger),
        )
        return job_id

    def update_job(self, job_id: str, **fields: Any) -> None:
        if not fields:
            return
        cols = ", ".join(f"{k} = ?" for k in fields)
        self.conn.execute(
            f"UPDATE jobs SET {cols} WHERE job_id = ?",
            (*fields.values(), job_id),
        )

    def list_jobs(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM jobs ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
