import sqlite3
import threading
import time
from pathlib import Path

from kb_core.stores.sqlite_store import SQLiteStore


def test_journal_mode_is_wal(tmp_path: Path):
    store = SQLiteStore(tmp_path / "t.db")
    mode = store.conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode == "wal"
    raw = sqlite3.connect(tmp_path / "t.db")
    assert raw.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_busy_timeout_configured(tmp_path: Path):
    store = SQLiteStore(tmp_path / "t.db")
    timeout_us = store.conn.execute("PRAGMA busy_timeout").fetchone()[0]
    assert timeout_us >= 5000


def test_reader_not_blocked_by_writer(tmp_path: Path):
    store = SQLiteStore(tmp_path / "t.db")
    store.init_schema()
    store.conn.execute("BEGIN EXCLUSIVE")
    try:
        store.conn.execute("CREATE TABLE IF NOT EXISTS t (x INTEGER)")

        other = sqlite3.connect(tmp_path / "t.db", timeout=2.0)
        other.execute("PRAGMA busy_timeout = 2000")
        got = other.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
        assert got >= 0
        other.close()
    finally:
        store.conn.execute("COMMIT")


def test_concurrent_write_with_busy_timeout(tmp_path: Path):
    store = SQLiteStore(tmp_path / "t.db")
    store.init_schema()
    store.conn.execute("CREATE TABLE IF NOT EXISTS counter (id INTEGER PRIMARY KEY, n INTEGER)")
    store.conn.execute("INSERT INTO counter VALUES (1, 0)")

    def bump() -> None:
        s = SQLiteStore(tmp_path / "t.db")
        for _ in range(20):
            s.conn.execute("UPDATE counter SET n = n + 1 WHERE id = 1")
            time.sleep(0.001)

    threads = [threading.Thread(target=bump) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)

    final = store.conn.execute("SELECT n FROM counter WHERE id = 1").fetchone()[0]
    assert final == 60
