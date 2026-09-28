import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from kb_cli.commands.jobs import scan_and_index
from kb_core.stores.sqlite_store import SQLiteStore

_NOW = datetime.now().isoformat()


def _insert_watch(store: SQLiteStore, path: str, recursive: int = 1) -> None:
    store.conn.execute(
        """INSERT INTO watch_dirs(path, project_name, project_strategy, file_types,
           exclude_patterns, recursive, created_at, include_patterns)
           VALUES (?,?,?,?,?,?,?,?)""",
        (
            path,
            "proj",
            "first_subdir",
            "[]",
            json.dumps(["**/node_modules/**"]),
            recursive,
            _NOW,
            json.dumps(["*/docs/*", "docs/*"]),
        ),
    )
    store.conn.commit()


def _store_with_watch(tmp_path: Path, sub: str) -> SQLiteStore:
    store = SQLiteStore(tmp_path / "t.db")
    store.init_schema()
    root = tmp_path / sub
    (root / "docs").mkdir(parents=True)
    (root / "src").mkdir(parents=True)
    _insert_watch(store, str(root).replace("\\", "/"))
    return store


def test_scan_indexes_only_matching_files(tmp_path: Path):
    store = _store_with_watch(tmp_path, "proj")
    root = tmp_path / "proj"
    (root / "docs" / "a.md").write_text("# A", encoding="utf-8")
    (root / "docs" / "b.md").write_text("# B", encoding="utf-8")
    (root / "src" / "c.php").write_text("<?php", encoding="utf-8")
    (root / "d.md").write_text("# D", encoding="utf-8")

    pipeline = MagicMock()
    processed, failed = scan_and_index(store, pipeline)

    assert (processed, failed) == (2, 0)
    indexed = {call.args[0].name for call in pipeline.index_file.call_args_list}
    assert indexed == {"a.md", "b.md"}


def test_scan_counts_failures(tmp_path: Path):
    store = _store_with_watch(tmp_path, "proj")
    (tmp_path / "proj" / "docs" / "a.md").write_text("# A", encoding="utf-8")
    (tmp_path / "proj" / "docs" / "b.md").write_text("# B", encoding="utf-8")

    pipeline = MagicMock()
    pipeline.index_file.side_effect = [None, RuntimeError("boom")]
    failures: list[str] = []

    def on_fail(full: Path, e: Exception) -> None:
        failures.append(full.name)

    processed, failed = scan_and_index(store, pipeline, on_fail=on_fail)

    assert (processed, failed) == (1, 1)
    assert failures == ["b.md"]


def test_scan_skips_missing_watch_root(tmp_path: Path):
    store = SQLiteStore(tmp_path / "t.db")
    store.init_schema()
    _insert_watch(store, str(tmp_path / "nope").replace("\\", "/"))
    pipeline = MagicMock()
    processed, failed = scan_and_index(store, pipeline)
    assert (processed, failed) == (0, 0)
    pipeline.index_file.assert_not_called()
