#!/bin/sh
# Central-side PERSONAL sync bundle exporter (runs on 192.168.0.10, systemd timer 17:40).
# Produces /data/RAG/sync/kb-personal-$AUTHOR.db : a filtered SQLite containing
#   - documents WHERE author = $AUTHOR
#   - chunks of those documents
#   - FULL embedding_cache (content-hash keyed, lets the local side rebuild
#     Qdrant vectors WITHOUT running the model)
#   - watch_dirs emptied (central paths are meaningless locally)
# Vectors are NOT exported; the consumer rebuilds them from the cache.

set -e
AUTHOR="${KB_SYNC_AUTHOR:-pingtao.cao}"
SYNC_DIR=/data/RAG/sync
DB=/home/caopingtao/.kb/kb_meta.db
OUT="$SYNC_DIR/kb-personal-$AUTHOR.db"
LOG=/home/caopingtao/.kb/export.log

mkdir -p "$SYNC_DIR"
echo "[$(date '+%F %T')] personal export start (author=$AUTHOR)" >> "$LOG"

python3 - "$DB" "$OUT.tmp" "$AUTHOR" <<'PYEOF'
import sqlite3, sys

src_path, dst_path, author = sys.argv[1], sys.argv[2], sys.argv[3]
src = sqlite3.connect(f"file:{src_path}?mode=ro", uri=True)
dst = sqlite3.connect(dst_path)

src.backup(dst)  # schema + data, then prune

cur = dst.cursor()
personal_docs = cur.execute(
    "SELECT COUNT(*) FROM documents WHERE author = ?", (author,)
).fetchone()[0]
cur.execute(
    """DELETE FROM chunks WHERE doc_id NOT IN
       (SELECT doc_id FROM documents WHERE author = ?)""", (author,)
)
cur.execute("DELETE FROM documents WHERE author != ?", (author,))
cur.execute("DELETE FROM watch_dirs")
cur.execute("DELETE FROM jobs")
dst.commit()

print(
    f"personal db: docs={personal_docs} "
    f"chunks={cur.execute('SELECT COUNT(*) FROM chunks').fetchone()[0]} "
    f"cache={cur.execute('SELECT COUNT(*) FROM embedding_cache').fetchone()[0]}"
)
dst.close(); src.close()
PYEOF

mv "$OUT.tmp" "$OUT"
ls -lh "$OUT" >> "$LOG"
echo "[$(date '+%F %T')] personal export done" >> "$LOG"
