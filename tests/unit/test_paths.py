from pathlib import Path

import pytest

from kb_core.enums import ProjectStrategy
from kb_core.utils.paths import infer_project, match_exclude, rel_path


def test_fixed_strategy_returns_project_name():
    p = infer_project(
        file_path=Path("D:/Notes/sub/a.md"),
        watch_dir=Path("D:/Notes"),
        strategy=ProjectStrategy.FIXED,
        project_name="notes",
    )
    assert p == "notes"


def test_first_subdir_strategy_returns_first_segment():
    p = infer_project(
        file_path=Path("C:/Glow/projects/yaf/src/Login.php"),
        watch_dir=Path("C:/Glow/projects"),
        strategy=ProjectStrategy.FIRST_SUBDIR,
        project_name="dev_projects",
    )
    assert p == "yaf"


def test_first_subdir_when_file_directly_in_watch(tmp_path: Path):
    f = tmp_path / "a.py"
    f.write_text("x")
    p = infer_project(
        file_path=f, watch_dir=tmp_path,
        strategy=ProjectStrategy.FIRST_SUBDIR, project_name="root",
    )
    assert p == "root"


def test_rel_path_posix_style():
    rp = rel_path(Path("C:/Glow/projects/yaf/src/a.php"), Path("C:/Glow/projects"))
    assert rp == "yaf/src/a.php"


def test_match_exclude_glob():
    assert match_exclude("yaf/vendor/x.php", ["**/vendor/**"])
    assert match_exclude("yaf/.git/config", ["**/.git/**"])
    assert not match_exclude("yaf/src/a.php", ["**/vendor/**"])
