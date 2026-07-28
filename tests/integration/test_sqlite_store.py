import json
from datetime import datetime
from pathlib import Path

import pytest

from kb_core.enums import ChunkType, DocStatus, FileType
from kb_core.models import Chunk, Document
from kb_core.stores.sqlite_store import SQLiteStore


@pytest.fixture
def store(tmp_path: Path) -> SQLiteStore:
    s = SQLiteStore(tmp_path / "t.db")
    s.init_schema()
    return s


def _make_doc(doc_id: str = "d1", source: str = "/p/a.php") -> Document:
    return Document(
        doc_id=doc_id, source_path=source, rel_path="p/a.php", project="p",
        file_type=FileType.CODE, language="php", sha256="h", size_bytes=10,
        mtime=datetime(2026, 7, 22), ingested_at=datetime(2026, 7, 22),
        embedding_version="bge-m3-v1", parser_version="ts",
    )


def _make_chunk(cid: str, oid: int) -> Chunk:
    return Chunk(
        chunk_id=cid, doc_id="d1", ordinal=oid, text="x", tokens=1,
        content_hash="ch", start_char=0, end_char=1,
        chunk_type=ChunkType.PARAGRAPH, quality_score=1.0,
    )


def test_upsert_and_get_document(store: SQLiteStore):
    doc = _make_doc()
    store.upsert_document(doc)
    got = store.get_document("d1")
    assert got is not None
    assert got.project == "p"
    assert got.status == DocStatus.ACTIVE


def test_upsert_document_replaces_on_same_id(store: SQLiteStore):
    store.upsert_document(_make_doc())
    modified = _make_doc()
    modified.project = "changed"
    store.upsert_document(modified)
    got = store.get_document("d1")
    assert got.project == "changed"


def test_get_document_by_path(store: SQLiteStore):
    store.upsert_document(_make_doc(source="/p/b.php"))
    got = store.get_document_by_path("/p/b.php")
    assert got is not None
    assert got.doc_id == "d1"


def test_upsert_chunks_and_query(store: SQLiteStore):
    store.upsert_document(_make_doc())
    store.upsert_chunks([_make_chunk("c1", 0), _make_chunk("c2", 1)])
    chunks = store.get_chunks_by_doc("d1")
    assert len(chunks) == 2
    assert chunks[0].ordinal == 0


def test_delete_chunks_of_doc(store: SQLiteStore):
    store.upsert_document(_make_doc())
    store.upsert_chunks([_make_chunk("c1", 0), _make_chunk("c2", 1)])
    n = store.delete_chunks_of_doc("d1")
    assert n == 2
    assert store.get_chunks_by_doc("d1") == []


def test_mark_document_deleted(store: SQLiteStore):
    store.upsert_document(_make_doc())
    store.mark_document_deleted("d1")
    got = store.get_document("d1")
    assert got.status == DocStatus.DELETED


def test_get_neighbor_chunk_ids(store: SQLiteStore):
    store.upsert_document(_make_doc())
    store.upsert_chunks([_make_chunk("c1", 0), _make_chunk("c2", 1), _make_chunk("c3", 2)])
    prev, nxt = store.get_neighbor_chunk_ids("c2")
    assert prev == "c1"
    assert nxt == "c3"
    prev_first, nxt_first = store.get_neighbor_chunk_ids("c1")
    assert prev_first is None
    assert nxt_first == "c2"


def test_watch_dir_crud(store: SQLiteStore):
    wid = store.add_watch_dir("/x", "p1", "fixed", True, [])
    assert wid > 0
    dirs = store.list_watch_dirs()
    assert len(dirs) == 1
    assert dirs[0]["path"] == "/x"
    store.remove_watch_dir(wid)
    assert store.list_watch_dirs() == []


def test_watch_dir_persists_file_types(store: SQLiteStore):
    wid = store.add_watch_dir(
        "/y", "p2", "fixed", True, [], file_types=["md", "txt"]
    )
    dirs = store.list_watch_dirs()
    assert len(dirs) == 1
    assert json.loads(dirs[0]["file_types"]) == ["md", "txt"]
    store.remove_watch_dir(wid)


def test_jobs_lifecycle(store: SQLiteStore):
    jid = store.create_job("incremental", "manual")
    assert jid
    store.update_job(jid, status="running", total_files=10)
    store.update_job(jid, status="success", finished_at="2026-07-22", processed_files=10)
    jobs = store.list_jobs()
    assert len(jobs) == 1
    assert jobs[0]["status"] == "success"
