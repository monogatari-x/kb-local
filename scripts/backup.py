"""备份知识库原始文档与 SQLite 索引到远程服务器。

增量:本地维护 sha256 清单,只推送变更/新增文件;远端只增不删(除非 --prune-stale)。
恢复:远端镜像 + kb_meta.db 快照即可在新机器重建,向量库可再 `kb jobs run` 生成。

用法:
    uv run python scripts/backup.py --dry-run
    uv run python scripts/backup.py
    uv run python scripts/backup.py --prune-stale
"""

import json
import os
import re
import shlex
import shutil
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

import typer
from rich.console import Console
from rich.markup import escape as rich_escape

from kb_core.config import WatchDirConfig, load_settings
from kb_core.stores.sqlite_store import SQLiteStore
from kb_core.utils.hashing import sha256_of_file
from kb_core.utils.paths import match_exclude, match_include, rel_path

console = Console()

BACKUP_META_NAME = "backup_meta.json"


@dataclass(frozen=True)
class FileState:
    size: int
    sha256: str


def _watch_dir_from_row(row: dict[str, Any]) -> WatchDirConfig:
    raw = row.get("exclude_patterns") or "[]"
    patterns: list[str] = raw if isinstance(raw, list) else json.loads(raw)
    raw_ft = row.get("file_types") or "[]"
    ftypes: list[str] = raw_ft if isinstance(raw_ft, list) else json.loads(raw_ft)
    raw_inc = row.get("include_patterns") or "[]"
    includes: list[str] = raw_inc if isinstance(raw_inc, list) else json.loads(raw_inc)
    return WatchDirConfig(
        path=str(row["path"]),
        project_name=str(row["project_name"]),
        project_strategy=str(row["project_strategy"]),
        recursive=bool(row["recursive"]),
        file_types=ftypes,
        include_patterns=includes,
        exclude_patterns=patterns,
    )


def collect_file_entries(watch_configs: list[WatchDirConfig]) -> dict[str, Path]:
    """复刻 `kb jobs run` 的文件选择规则,保证"索引了什么就备份什么"。

    返回 {远端相对路径: 本地路径}。远端相对路径取相对 watch root
    (如 yaf/docs/x.md)——服务器归档结构统一为
    /data/RAG/bak/<author>/<project>/docs/...,不镜像本机盘符/中间层,
    这样中心实例的 watch 路径对所有人都一样。
    """
    entries: dict[str, Path] = {}
    for wd in watch_configs:
        root = Path(wd.path).expanduser()
        if not root.exists():
            continue
        allowed = {e.lower().lstrip(".") for e in wd.file_types}
        for current_root, _dirs, files in os.walk(root):
            for f in files:
                full = Path(current_root) / f
                if allowed and full.suffix.lower().lstrip(".") not in allowed:
                    continue
                rp = rel_path(full, root)
                if not match_include(rp, wd.include_patterns):
                    continue
                if match_exclude(rp, wd.exclude_patterns):
                    continue
                entries[rp] = full
            if not wd.recursive:
                break
    return entries


def snapshot_sqlite(src: Path, dest: Path) -> None:
    """SQLite backup API 保证一致快照,WAL 模式直接拷贝文件可能损坏。"""
    src_conn = sqlite3.connect(f"file:///{src.as_posix()}?mode=ro", uri=True)
    dest_conn = sqlite3.connect(dest)
    try:
        src_conn.backup(dest_conn)
    finally:
        dest_conn.close()
        src_conn.close()


def compute_states(files: dict[str, Path]) -> dict[str, FileState]:
    return {rel: FileState(p.stat().st_size, sha256_of_file(p)) for rel, p in files.items()}


def plan_sync(
    current: dict[str, FileState], manifest: dict[str, FileState]
) -> tuple[list[str], list[str]]:
    to_push = [rel for rel, st in current.items() if manifest.get(rel) != st]
    stale = [rel for rel in manifest if rel not in current]
    return sorted(to_push), sorted(stale)


def _msys(path: Path) -> str:
    """msys scp 会把 D: 误判为远程主机,需转成 /d/ 形式。"""
    posix = path.as_posix()
    m = re.match(r"^([A-Za-z]):/(.*)$", posix)
    return f"/{m.group(1).lower()}/{m.group(2)}" if m else posix


def _ssh_bin(name: str) -> tuple[str, bool]:
    """优先 Windows 原生 OpenSSH,定时任务环境通常没有 msys scp。"""
    root = os.environ.get("SYSTEMROOT")
    if root:
        candidate = Path(root) / "System32" / "OpenSSH" / f"{name}.exe"
        if candidate.exists():
            return str(candidate), False
    return shutil.which(name) or name, True


def _path_arg(path: Path, msys: bool) -> str:
    return _msys(path) if msys else path.as_posix()


def _run_with_retry(args: list[str], desc: str, attempts: int = 3, delay_s: float = 3.0) -> None:
    """ssh 偶发 exit 255(连接抖动)会让整次备份失败;重试扛过瞬时故障。"""
    for i in range(1, attempts + 1):
        proc = subprocess.run(args, capture_output=True, text=True)
        if proc.returncode == 0:
            return
        if proc.stdout:
            console.print(f"[dim]{proc.stdout.strip()[:200]}[/dim]")
        if i == attempts:
            console.print(
                f"[red]FAIL[/red] {desc}: exit {proc.returncode} {proc.stderr.strip()[:200]}"
            )
            raise subprocess.CalledProcessError(proc.returncode, args, proc.stdout, proc.stderr)
        console.print(f"[yellow]retry {i}/{attempts - 1}[/yellow] {desc}: exit {proc.returncode}")
        time.sleep(delay_s)


def _ssh(user: str, server: str, key: Path, command: str) -> None:
    binary, msys = _ssh_bin("ssh")
    args = [
        binary,
        "-i",
        _path_arg(key, msys),
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=accept-new",
        f"{user}@{server}",
        command,
    ]
    console.print(f"[dim]ssh {command}[/dim]")
    _run_with_retry(args, f"ssh {command}")


def _scp(user: str, server: str, key: Path, local: list[Path], remote_target: str) -> None:
    binary, msys = _ssh_bin("scp")
    args = [
        binary,
        "-i",
        _path_arg(key, msys),
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=accept-new",
        *[_path_arg(p, msys) for p in local],
        f"{user}@{server}:{remote_target}",
    ]
    console.print(f"[dim]scp {len(local)} 个文件 → {remote_target}[/dim]")
    _run_with_retry(args, f"scp {len(local)} files -> {remote_target}")


def _push_files(
    files: dict[str, Path],
    rels: list[str],
    *,
    user: str,
    server: str,
    key: Path,
    remote_root: str,
) -> None:
    groups: dict[str, list[str]] = {}
    for rel in rels:
        parent = rel.rpartition("/")[0] if "/" in rel else ""
        groups.setdefault(parent, []).append(rel)
    dirs = [remote_root] + sorted(f"{remote_root}/{p}" for p in groups)
    _ssh(user, server, key, "mkdir -p " + " ".join(shlex.quote(d) for d in dirs))
    for parent, group in sorted(groups.items()):
        target = remote_root if not parent else f"{remote_root}/{parent}"
        _scp(user, server, key, [files[r] for r in group], f"{target}/")


def _prune_remote(user: str, server: str, key: Path, remote_root: str, rels: list[str]) -> None:
    targets = [f"{remote_root}/{r}" for r in rels]
    _ssh(user, server, key, "rm -f " + " ".join(shlex.quote(t) for t in targets))


def _write_meta(tmp_dir: Path, docs_count: int, total_bytes: int) -> Path:
    meta = {
        "created_at": datetime.now().isoformat(),
        "docs_files": docs_count,
        "total_bytes": total_bytes,
    }
    p = tmp_dir / BACKUP_META_NAME
    p.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def _load_manifest(path: Path) -> dict[str, FileState]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        str(k): FileState(int(v["size"]), str(v["sha256"]))
        for k, v in data.items()
        if isinstance(v, dict)
    }


def _save_manifest(path: Path, manifest: dict[str, FileState]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {k: {"size": v.size, "sha256": v.sha256} for k, v in manifest.items()}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main(
    config: str = typer.Option(None, "--config", envvar="KB_CONFIG_PATH", help="kb 配置文件"),
    server: str = typer.Option("", "--server", help="远程服务器(默认读 config backup.server)"),
    user: str = typer.Option("", "--user", help="SSH 用户名(默认读 backup.user)"),
    key: str = typer.Option("", "--key", help="SSH 私钥路径(默认读 backup.key)"),
    remote: str = typer.Option("", "--remote", help="远端备份根目录(默认读 backup.remote_root)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只列出计划,不传输"),
    prune_stale: bool = typer.Option(False, "--prune-stale", help="同步删除远端已不存在的文件"),
) -> None:
    settings = load_settings(Path(config) if config else None)
    server = server or settings.backup.server
    user = user or settings.backup.user
    key = key or settings.backup.key
    remote = remote or settings.backup.remote_root
    sqlite_path = Path(settings.database.sqlite_path).expanduser()
    store = SQLiteStore(sqlite_path)
    store.init_schema()
    watch_configs = list(settings.watch_dirs) or [
        _watch_dir_from_row(d) for d in store.list_watch_dirs()
    ]
    store.close()

    tmp_dir = sqlite_path.parent / "backup_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    files: dict[str, Path] = collect_file_entries(watch_configs)
    snap = tmp_dir / "kb_meta.db"
    snapshot_sqlite(sqlite_path, snap)
    files["kb_meta.db"] = snap

    current = compute_states(files)
    manifest_path = sqlite_path.parent / "backup_manifest.json"
    manifest = _load_manifest(manifest_path)
    to_push, stale = plan_sync(current, manifest)

    console.print(
        f"[bold]kb-backup[/bold] docs={len(files) - 1} 推送={len(to_push)} 远端冗余={len(stale)}"
    )
    for rel in sorted(current):
        action = "PUSH" if rel in to_push else "skip"
        console.print(f"  {action:<4} {rich_escape(rel)}")
    for rel in stale:
        console.print(f"  stale {rich_escape(rel)}")

    if dry_run:
        console.print("[yellow]dry-run:未执行任何传输[/yellow]")
        return

    key_path = Path(key).expanduser()
    if not key_path.exists():
        raise typer.BadParameter(f"SSH key not found: {key_path}")

    author = settings.author.strip()
    if not author:
        console.print(
            "[red]未配置 author,拒绝备份。[/red]在 ~/.kb/config.yaml 加 `author: <禅道账号>`"
            "(备份按人分目录,是工作交接/评价的依据,不能匿名)"
        )
        raise typer.Exit(code=1)
    remote_root = f"{remote.rstrip('/')}/{author}"
    if to_push:
        _push_files(files, to_push, user=user, server=server, key=key_path, remote_root=remote_root)
    if prune_stale and stale:
        _prune_remote(user, server, key_path, remote_root, stale)
    meta = _write_meta(tmp_dir, len(files) - 1, sum(p.stat().st_size for p in files.values()))
    _scp(user, server, key_path, [meta], f"{remote_root}/")

    _save_manifest(manifest_path, current)
    console.print(f"[green]完成[/green] 推送 {len(to_push)} 个文件,清单已更新 {manifest_path}")


if __name__ == "__main__":
    typer.run(main)
