import json
import sqlite3
import struct
from datetime import datetime
from typing import Any


class EmbeddingCache:
    def __init__(self, conn: sqlite3.Connection, version: str):
        self.conn = conn
        self.version = version
        self._hits = 0
        self._misses = 0

    def get(self, content_hash: str) -> tuple[list[float], dict[str, Any]] | None:
        row = self.conn.execute(
            "SELECT dense_vector, sparse_indices, sparse_values FROM embedding_cache "
            "WHERE content_hash = ? AND embedding_version = ?",
            (content_hash, self.version),
        ).fetchone()
        if row is None:
            self._misses += 1
            return None
        self._hits += 1
        dense = self._decode_dense(row["dense_vector"])
        sparse = {
            "indices": json.loads(row["sparse_indices"] or "[]"),
            "values": json.loads(row["sparse_values"] or "[]"),
        }
        return dense, sparse

    def put(self, content_hash: str, dense: list[float], sparse: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO embedding_cache
               (content_hash, embedding_version, dense_vector,
                sparse_indices, sparse_values, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (content_hash, self.version,
             self._encode_dense(dense),
             json.dumps(sparse.get("indices", [])),
             json.dumps(sparse.get("values", [])),
             datetime.now().isoformat()),
        )

    def stats(self) -> dict[str, int]:
        row = self.conn.execute(
            "SELECT COUNT(*) AS n FROM embedding_cache WHERE embedding_version = ?",
            (self.version,),
        ).fetchone()
        return {"hits": self._hits, "misses": self._misses, "size": row["n"]}

    @staticmethod
    def _encode_dense(vec: list[float]) -> bytes:
        return struct.pack(f"{len(vec)}f", *vec)

    @staticmethod
    def _decode_dense(blob: bytes) -> list[float]:
        n = len(blob) // 4
        return list(struct.unpack(f"{n}f", blob))
