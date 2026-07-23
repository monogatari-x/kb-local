import fnmatch
from pathlib import PurePath, PurePosixPath

from kb_core.enums import ProjectStrategy


def infer_project(
    file_path: PurePath,
    watch_dir: PurePath,
    strategy: ProjectStrategy,
    project_name: str,
) -> str:
    if strategy == ProjectStrategy.FIXED:
        return project_name
    try:
        rel = file_path.relative_to(watch_dir)
    except ValueError:
        return project_name
    parts = rel.parts
    if len(parts) <= 1:
        return project_name
    return parts[0]


def rel_path(file_path: PurePath, watch_dir: PurePath) -> str:
    try:
        rel = file_path.relative_to(watch_dir)
    except ValueError:
        rel = PurePath(file_path.name)
    return PurePosixPath(*rel.parts).as_posix()


def match_exclude(rel_path_str: str, patterns: list[str]) -> bool:
    for pat in patterns:
        norm_pat = pat.replace("\\", "/")
        if fnmatch.fnmatch(rel_path_str, norm_pat):
            return True
        if "**" in norm_pat:
            stripped = norm_pat.replace("**/", "").replace("/**", "")
            if stripped and stripped in rel_path_str:
                return True
    return False
