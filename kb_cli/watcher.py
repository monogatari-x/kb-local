"""文件监听:watchdog 触发 → 去抖 → pipeline.index_file。"""

import json
import sys
import threading
import time
import traceback
from pathlib import Path, PurePosixPath

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers.api import BaseObserver

from kb_core.enums import ProjectStrategy
from kb_core.pipelines.indexing import IndexingPipeline
from kb_core.stores.sqlite_store import SQLiteStore
from kb_core.utils.paths import match_exclude, match_include


class DebouncedIndexHandler(FileSystemEventHandler):
    def __init__(
        self,
        pipeline: IndexingPipeline,
        watch_dir: Path,
        project_name: str,
        project_strategy: str,
        exclude_patterns: list[str],
        file_types: list[str] | None = None,
        include_patterns: list[str] | None = None,
        debounce_seconds: float = 2.0,
    ) -> None:
        super().__init__()
        self.pipeline = pipeline
        self.watch_dir = watch_dir
        self.project_name = project_name
        self.project_strategy = project_strategy
        self.exclude_patterns = exclude_patterns
        self.include_patterns = include_patterns or []
        self.file_types = [e.lower().lstrip(".") for e in (file_types or [])]
        self.debounce_seconds = debounce_seconds
        self._last_indexed: dict[Path, float] = {}
        self._lock = threading.Lock()
        self.index_count = 0

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        if event.event_type not in ("created", "modified", "moved"):
            return
        src_str = event.src_path if isinstance(event.src_path, str) else str(event.src_path)
        src_path = Path(src_str)
        if self.file_types and src_path.suffix.lower().lstrip(".") not in self.file_types:
            return
        try:
            rel = src_path.relative_to(self.watch_dir)
        except ValueError:
            rel = src_path
        rel_posix = PurePosixPath(*rel.parts).as_posix() if hasattr(rel, "parts") else str(rel)
        if not match_include(rel_posix, self.include_patterns):
            return
        if match_exclude(rel_posix, self.exclude_patterns):
            return
        now = time.monotonic()
        with self._lock:
            last = self._last_indexed.get(src_path, 0.0)
            if now - last < self.debounce_seconds:
                return
            self._last_indexed[src_path] = now
        try:
            self.pipeline.index_file(
                src_path,
                watch_dir=self.watch_dir,
                project_strategy=ProjectStrategy(self.project_strategy),
                project_name=self.project_name,
            )
            self.index_count += 1
        except Exception as e:
            sys.stderr.write(
                f"[watcher] index failed: {src_path}: {type(e).__name__}: {e}\n"
                f"{traceback.format_exc(limit=3)}"
            )
            sys.stderr.flush()


def start_watcher(
    store: SQLiteStore,
    pipeline: IndexingPipeline,
    debounce_seconds: float = 2.0,
) -> BaseObserver:
    from watchdog.observers import Observer

    watch_dirs = store.list_watch_dirs()
    observer = Observer()
    for wd in watch_dirs:
        path = Path(str(wd["path"])).expanduser()
        if not path.exists():
            continue
        raw = wd.get("exclude_patterns") or "[]"
        patterns: list[str] = raw if isinstance(raw, list) else json.loads(raw)
        raw_ft = wd.get("file_types") or "[]"
        ftypes: list[str] = raw_ft if isinstance(raw_ft, list) else json.loads(raw_ft)
        raw_inc = wd.get("include_patterns") or "[]"
        includes: list[str] = raw_inc if isinstance(raw_inc, list) else json.loads(raw_inc)
        handler = DebouncedIndexHandler(
            pipeline=pipeline,
            watch_dir=path,
            project_name=str(wd["project_name"]),
            project_strategy=str(wd["project_strategy"]),
            exclude_patterns=patterns,
            file_types=ftypes,
            include_patterns=includes,
            debounce_seconds=debounce_seconds,
        )
        observer.schedule(handler, str(path), recursive=bool(wd["recursive"]))
    observer.start()
    return observer
