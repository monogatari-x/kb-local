import json
from datetime import datetime
from pathlib import Path

from watchdog.events import FileCreatedEvent

from kb_cli.commands.jobs import scan_and_index
from kb_cli.watcher import DebouncedIndexHandler
from kb_core.config import WatchDirConfig
from kb_core.stores.sqlite_store import SQLiteStore

_NOW = datetime.now().isoformat()


def _insert_watch(store: SQLiteStore, path: str, author: str) -> None:
    store.conn.execute(
        """INSERT INTO watch_dirs(path, project_name, project_strategy, file_types,
           exclude_patterns, recursive, created_at, include_patterns, author)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (path, "proj", "first_subdir", "[]", "[]", 1, _NOW, json.dumps(["docs/*"]), author),
    )
    store.conn.commit()


def test_add_watch_dir_persists_author(tmp_path: Path):
    store = SQLiteStore(tmp_path / "t.db")
    store.init_schema()
    wid = store.add_watch_dir("X:/p", "p", "fixed", True, [], author="pingtao.cao")
    row = store.conn.execute("SELECT author FROM watch_dirs WHERE id = ?", (wid,)).fetchone()
    assert row["author"] == "pingtao.cao"


def test_scan_passes_watch_author(tmp_path: Path):
    store = SQLiteStore(tmp_path / "t.db")
    store.init_schema()
    for name, author in (("alice", "a.zhang"), ("bob", "b.li")):
        root = tmp_path / name / "Projects"
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "f.md").write_text("# x", encoding="utf-8")
        _insert_watch(store, str(root).replace("\\", "/"), author)

    calls: list[str | None] = []

    class FakePipeline:
        def index_file(self, path, watch_dir, project_strategy, project_name, author=None):  # type: ignore[no-untyped-def]
            calls.append(author)
            return "id"

    processed, failed = scan_and_index(store, FakePipeline())  # type: ignore[arg-type]
    assert (processed, failed) == (2, 0)
    assert sorted(c for c in calls if c) == ["a.zhang", "b.li"]


def test_scan_empty_watch_author_falls_back_to_pipeline_default(tmp_path: Path):
    store = SQLiteStore(tmp_path / "t.db")
    store.init_schema()
    root = tmp_path / "carol" / "Projects"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "f.md").write_text("# x", encoding="utf-8")
    _insert_watch(store, str(root).replace("\\", "/"), "")

    calls: list[str | None] = []

    class FakePipeline:
        def index_file(self, path, watch_dir, project_strategy, project_name, author=None):  # type: ignore[no-untyped-def]
            calls.append(author)

    scan_and_index(store, FakePipeline())  # type: ignore[arg-type]
    assert calls == [None]


def test_watcher_handler_passes_author(tmp_path: Path):
    calls: list[str | None] = []

    class FakePipeline:
        def index_file(self, path, watch_dir, project_strategy, project_name, author=None):  # type: ignore[no-untyped-def]
            calls.append(author)

    handler = DebouncedIndexHandler(
        pipeline=FakePipeline(),  # type: ignore[arg-type]
        watch_dir=tmp_path,
        project_name="p",
        project_strategy="fixed",
        exclude_patterns=[],
        author="a.zhang",
    )
    handler.on_any_event(FileCreatedEvent(str(tmp_path / "docs" / "a.md")))
    assert calls == ["a.zhang"]


def test_watch_dir_config_has_author_default_empty():
    cfg = WatchDirConfig(path="X:/p", project_name="p")
    assert cfg.author == ""
