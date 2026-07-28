from pathlib import Path
from unittest.mock import MagicMock

from watchdog.events import (
    DirCreatedEvent,
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
)

from kb_cli.watcher import DebouncedIndexHandler


def _make_handler(**overrides):
    defaults: dict = {
        "pipeline": MagicMock(),
        "watch_dir": Path("/tmp"),
        "project_name": "test",
        "project_strategy": "fixed",
        "exclude_patterns": [],
        "file_types": [],
        "include_patterns": [],
        "debounce_seconds": 2.0,
    }
    defaults.update(overrides)
    return DebouncedIndexHandler(**defaults)


def test_handler_processes_created_event():
    h = _make_handler()
    h.on_any_event(FileCreatedEvent("/tmp/foo.php"))
    h.pipeline.index_file.assert_called_once()


def test_handler_debounces_rapid_events():
    h = _make_handler(debounce_seconds=1.0)
    h.on_any_event(FileModifiedEvent("/tmp/foo.php"))
    h.on_any_event(FileModifiedEvent("/tmp/foo.php"))
    assert h.pipeline.index_file.call_count == 1


def test_handler_skips_excluded():
    h = _make_handler(exclude_patterns=["*.log"])
    h.on_any_event(FileCreatedEvent("/tmp/foo.log"))
    h.pipeline.index_file.assert_not_called()


def test_handler_respects_file_types_allowlist():
    h = _make_handler(file_types=["md"])
    h.on_any_event(FileCreatedEvent("/tmp/foo.php"))
    h.pipeline.index_file.assert_not_called()


def test_handler_file_types_allows_listed_extension():
    h = _make_handler(file_types=["md"])
    h.on_any_event(FileCreatedEvent("/tmp/notes.md"))
    h.pipeline.index_file.assert_called_once()


def test_handler_empty_file_types_allows_all():
    h = _make_handler(file_types=[])
    h.on_any_event(FileCreatedEvent("/tmp/anything.php"))
    h.pipeline.index_file.assert_called_once()


def test_handler_respects_include_patterns():
    h = _make_handler(include_patterns=["docs/*", "CLAUDE.md"])
    h.on_any_event(FileCreatedEvent("/tmp/src/foo.md"))
    h.pipeline.index_file.assert_not_called()


def test_handler_include_patterns_allows_matching_path():
    h = _make_handler(include_patterns=["docs/*", "CLAUDE.md"])
    h.on_any_event(FileCreatedEvent("/tmp/docs/arch.md"))
    h.pipeline.index_file.assert_called_once()


def test_handler_include_patterns_allows_named_root_file():
    h = _make_handler(include_patterns=["docs/*", "CLAUDE.md"])
    h.on_any_event(FileCreatedEvent("/tmp/CLAUDE.md"))
    h.pipeline.index_file.assert_called_once()


def test_handler_ignores_directory_events():
    h = _make_handler()
    h.on_any_event(DirCreatedEvent("/tmp/subdir"))
    h.pipeline.index_file.assert_not_called()


def test_handler_ignores_unknown_event_types():
    h = _make_handler()
    h.on_any_event(FileDeletedEvent("/tmp/foo.php"))
    h.pipeline.index_file.assert_not_called()
