"""从 kb_meta.db 的 chunks + embedding_cache 重建本机 Qdrant 向量库。

用于离线副本恢复:中心的个人库快照带了全量嵌入缓存,本机无需加载
模型即可把向量灌回 Qdrant(kb_search 立即可用)。

用法:
    uv run python scripts/rebuild_qdrant_from_cache.py [--db ~/.kb/kb_meta.db]
"""

import argparse
import json
import sqlite3
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from kb_core.models import Chunk
from kb_core.enums import ChunkType
from kb_core.stores.qdrant_store import QdrantStore
from kb_core.config import load_settings

BATCH = 500


def _row_to_chunk(row: sqlite3.Row) -> Chunk:
    meta = json.loads(row["meta"] or "{}")
    return Chunk(
        chunk_id=row["chunk_id"],
        doc_id=row["doc_id"],
        ordinal=row["ordinal"],
        text=row["text"],
        tokens=row["tokens"],
        content_hash=row["content_hash"],
        start_char=row["start_char"],
        end_char=row["end_char"],
        start_line=row["start_line"],
        end_line=row["end_line"],
        section_path=row["section_path"],
        symbol_path=row["symbol_path"],
        chunk_type=ChunkType(row["chunk_type"]),
        quality_score=row["quality_score"],
        language=row["language"],
        meta=meta,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=None)
    args = parser.parse_args()

    settings = load_settings(None)
    db_path = Path(args.db or settings.database.sqlite_path).expanduser()
    con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    version = settings.embedding.version

    rows = con.execute(
        """SELECT c.* FROM chunks c
           JOIN embedding_cache e
             ON e.content_hash = c.content_hash AND e.embedding_version = ?
           ORDER BY c.doc_id, c.ordinal""",
        (version,),
    ).fetchall()
    total_docs = con.execute("SELECT COUNT(DISTINCT doc_id) FROM chunks").fetchone()[0]
    missing = con.execute(
        """SELECT COUNT(*) FROM chunks c WHERE NOT EXISTS (
             SELECT 1 FROM embedding_cache e
              WHERE e.content_hash = c.content_hash AND e.embedding_version = ?)""",
        (version,),
    ).fetchone()[0]
    print(f"docs={total_docs} chunks_with_cache={len(rows)} chunks_missing_cache={missing}")
    if missing:
        print(f"warning: {missing} chunks have no cached embedding and will be skipped")

    store = QdrantStore(url=settings.qdrant.url, collection=settings.qdrant.collection)
    try:
        store.delete_collection()
    except Exception:
        pass
    store.ensure_collection()

    done = 0
    for i in range(0, len(rows), BATCH):
        batch = rows[i : i + BATCH]
        chunks: list[Chunk] = []
        dense: list[list[float]] = []
        sparse: list[dict] = []
        for row in batch:
            blob = con.execute(
                "SELECT dense_vector, sparse_indices, sparse_values FROM embedding_cache "
                "WHERE content_hash = ? AND embedding_version = ?",
                (row["content_hash"], version),
            ).fetchone()
            n = len(blob["dense_vector"]) // 4
            chunks.append(_row_to_chunk(row))
            dense.append(list(struct.unpack(f"{n}f", blob["dense_vector"])))
            sparse.append(
                {
                    "indices": json.loads(blob["sparse_indices"] or "[]"),
                    "values": json.loads(blob["sparse_values"] or "[]"),
                }
            )
        store.upsert_chunks(chunks, dense, sparse)
        done += len(batch)
        print(f"  upserted {done}/{len(rows)}")

    print(f"done: collection rebuilt with {done} chunks from cache")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
