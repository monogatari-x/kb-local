import importlib.util
from pathlib import Path

from kb_core.config import WatchDirConfig

SCRIPTS = Path(__file__).parent.parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location("backup_script", SCRIPTS / "backup.py")
assert _spec is not None and _spec.loader is not None
backup = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(backup)


def test_collect_entries_keys_are_watch_relative(tmp_path: Path) -> None:
    _write("proj1/docs/a.md", "a", tmp_path)
    cfg = WatchDirConfig(
        path=str(tmp_path), project_name="glow", project_strategy="first_subdir"
    )
    entries = backup.collect_file_entries([cfg])
    assert list(entries) == ["proj1/docs/a.md"]


def _write(rel: str, content: str, tmp_path: Path) -> None:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def test_collect_files_respects_watch_rules(tmp_path: Path) -> None:
    _write("proj1/docs/a.md", "a", tmp_path)
    _write("proj1/docs/sub/b.md", "b", tmp_path)
    _write("proj1/doc/c.md", "c", tmp_path)
    _write("proj1/src/d.py", "d", tmp_path)
    _write("proj1/activeByKm/doc/e.md", "e", tmp_path)
    _write("proj2/docs/f.md", "f", tmp_path)
    cfg = WatchDirConfig(
        path=str(tmp_path),
        project_name="glow-projects",
        project_strategy="first_subdir",
        recursive=True,
        file_types=[],
        include_patterns=["*/docs/*", "*/doc/*"],
        exclude_patterns=["**/node_modules/**", "**/activeByKm/doc/**"],
    )
    got = set(backup.collect_file_entries([cfg]))
    assert got == {
        "proj1/docs/a.md",
        "proj1/docs/sub/b.md",
        "proj1/doc/c.md",
        "proj2/docs/f.md",
    }


def test_plan_sync_incremental() -> None:
    a = backup.FileState(size=3, sha256="aaa")
    b = backup.FileState(size=5, sha256="bbb")
    manifest = {"docs/x.md": a, "docs/gone.md": b}
    current = {"docs/x.md": a, "docs/y.md": backup.FileState(size=1, sha256="ccc")}
    to_push, stale = backup.plan_sync(current, manifest)
    assert to_push == ["docs/y.md"]
    assert stale == ["docs/gone.md"]
