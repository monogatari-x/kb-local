"""Re-setup watch_dirs: drop all, add per-project watch_dirs narrowed to memory files only.

Memory = root CLAUDE.md/AGENTS.md/GEMINI.md + .claude/** + docs/** + openspec/**
"""

from pathlib import Path

from kb_core.config import load_settings
from kb_core.stores.sqlite_store import SQLiteStore

INCLUDE = [
    "CLAUDE.md",
    "AGENTS.md",
    "GEMINI.md",
    ".claude/*",
    ".claude/**",
    "docs/*",
    "docs/**",
    "openspec/*",
    "openspec/**",
]
EXCLUDE = [
    "vendor/*",
    "*/vendor/*",
    "node_modules/*",
    "*/node_modules/*",
    ".git/*",
    "*/.git/*",
]
FILE_TYPES = ["md"]


def main() -> int:
    settings = load_settings(None)
    db_path = Path(settings.database.sqlite_path).expanduser()
    store = SQLiteStore(db_path)
    store.init_schema()

    print("Dropping existing watch_dirs...")
    for d in store.list_watch_dirs():
        store.remove_watch_dir(d["id"])

    print("Marking existing documents as deleted (will be re-indexed)...")
    store.conn.execute("UPDATE documents SET status = 'deleted'")

    projects_root = Path("C:/Glow/Projects")
    added = 0
    for d in sorted(projects_root.iterdir()):
        if not d.is_dir():
            continue
        path_str = str(d).replace("\\", "/")
        try:
            wid = store.add_watch_dir(
                path_str,
                d.name,
                "fixed",
                True,
                EXCLUDE,
                file_types=FILE_TYPES,
                include_patterns=INCLUDE,
            )
            print(f"  + #{wid} {d.name}")
            added += 1
        except Exception as e:
            print(f"  - skip {d.name}: {e}")

    print(f"\nAdded {added} watch_dirs")
    store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
