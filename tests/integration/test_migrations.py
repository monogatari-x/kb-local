import sqlite3


def test_all_tables_created(sqlite_db: sqlite3.Connection):
    cursor = sqlite_db.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    expected = {"documents", "chunks", "watch_dirs", "jobs", "tags", "settings", "embedding_cache"}
    assert expected.issubset(tables)


def test_chunks_cascade_delete(sqlite_db: sqlite3.Connection):
    sqlite_db.execute(
        "INSERT INTO documents(doc_id, source_path, rel_path, project, file_type, "
        "sha256, size_bytes, mtime, ingested_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("d1", "/p", "p", "yaf", "code", "h", 1, "2026-07-22", "2026-07-22"),
    )
    sqlite_db.execute(
        "INSERT INTO chunks(chunk_id, doc_id, ordinal, text, tokens, content_hash, "
        "start_char, end_char, chunk_type, quality_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("c1", "d1", 0, "hi", 1, "ch", 0, 2, "paragraph", 1.0),
    )
    sqlite_db.execute("DELETE FROM documents WHERE doc_id = ?", ("d1",))
    sqlite_db.commit()
    cursor = sqlite_db.execute("SELECT COUNT(*) FROM chunks WHERE doc_id = ?", ("d1",))
    assert cursor.fetchone()[0] == 0


def test_watch_dirs_path_unique(sqlite_db: sqlite3.Connection):
    sqlite_db.execute(
        "INSERT INTO watch_dirs(path, project_name, created_at) VALUES (?, ?, ?)",
        ("/x", "p", "2026-07-22"),
    )
    sqlite_db.commit()
    try:
        sqlite_db.execute(
            "INSERT INTO watch_dirs(path, project_name, created_at) VALUES (?, ?, ?)",
            ("/x", "p", "2026-07-22"),
        )
        sqlite_db.commit()
        raise AssertionError("Should have raised IntegrityError")
    except sqlite3.IntegrityError:
        pass


def test_embedding_cache_composite_pk(sqlite_db: sqlite3.Connection):
    sqlite_db.execute(
        "INSERT INTO embedding_cache(content_hash, embedding_version, dense_vector, created_at) "
        "VALUES (?, ?, ?, ?)",
        ("h1", "v1", b"\x00\x00", "2026-07-22"),
    )
    sqlite_db.execute(
        "INSERT INTO embedding_cache(content_hash, embedding_version, dense_vector, created_at) "
        "VALUES (?, ?, ?, ?)",
        ("h1", "v2", b"\x00\x00", "2026-07-22"),
    )
    sqlite_db.commit()
    cursor = sqlite_db.execute(
        "SELECT COUNT(*) FROM embedding_cache WHERE content_hash = ?", ("h1",)
    )
    assert cursor.fetchone()[0] == 2
