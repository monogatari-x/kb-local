import uuid
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from qdrant_client.http.exceptions import UnexpectedResponse

from kb_core.exceptions import VectorStoreError
from kb_core.models import Chunk

_QDRANT_NS = uuid.UUID("a3f1b9c0-0000-0000-0000-000000000001")


class QdrantStore:
    def __init__(self, url: str, collection: str, vector_size: int = 1024):
        self.collection = collection
        self.vector_size = vector_size
        self.client = QdrantClient(url=url)

    def ensure_collection(self) -> None:
        try:
            self.client.get_collection(self.collection)
            return
        except UnexpectedResponse as e:
            if e.status_code != 404:
                raise VectorStoreError(f"Cannot reach Qdrant: {e}") from e
        try:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config={
                    "dense": qm.VectorParams(
                        size=self.vector_size, distance=qm.Distance.COSINE
                    )
                },
                sparse_vectors_config={
                    "sparse": qm.SparseVectorParams(index=qm.SparseIndexParams())
                },
                quantization_config=qm.ScalarQuantization(
                    scalar=qm.ScalarQuantizationConfig(
                        type=qm.ScalarType.INT8, quantile=0.99, always_ram=True
                    )
                ),
            )
        except Exception as e:
            raise VectorStoreError(f"create_collection failed: {e}") from e

    def upsert_chunks(
        self,
        chunks: list[Chunk],
        dense_vectors: list[list[float]],
        sparse_vectors: list[dict[str, Any]],
    ) -> None:
        points = []
        for c, dense, sparse in zip(
            chunks, dense_vectors, sparse_vectors, strict=True
        ):
            points.append(
                qm.PointStruct(
                    id=str(uuid.uuid5(_QDRANT_NS, c.chunk_id)),
                    vector={
                        "dense": dense,
                        "sparse": qm.SparseVector(
                            indices=sparse["indices"], values=sparse["values"]
                        ),
                    },
                    payload={
                        "chunk_id": c.chunk_id,
                        "doc_id": c.doc_id,
                        "ordinal": c.ordinal,
                        "text_truncated": c.text_truncated,
                        "chunk_type": c.chunk_type.value,
                        "project": c.meta.get("project"),
                        "language": c.language,
                        "section_path": c.section_path,
                        "symbol_path": c.symbol_path,
                        "tags": c.meta.get("tags", []),
                        "quality_score": c.quality_score,
                        "content_hash": c.content_hash,
                        "embedding_version": c.meta.get("embedding_version"),
                    },
                )
            )
        try:
            self.client.upsert(
                collection_name=self.collection, points=points, wait=True
            )
        except Exception as e:
            raise VectorStoreError(f"upsert failed: {e}") from e

    def delete_by_doc(self, doc_id: str) -> None:
        try:
            self.client.delete(
                collection_name=self.collection,
                points_selector=qm.FilterSelector(
                    filter=qm.Filter(
                        must=[
                            qm.FieldCondition(
                                key="doc_id", match=qm.MatchValue(value=doc_id)
                            )
                        ]
                    )
                ),
                wait=True,
            )
        except Exception as e:
            raise VectorStoreError(f"delete_by_doc failed: {e}") from e

    def search_dense_sparse(
        self,
        dense: list[float],
        sparse: dict[str, Any],
        filters: dict[str, Any] | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        query_filter = qm.Filter(**filters) if filters else None
        try:
            results = self.client.query_points(
                collection_name=self.collection,
                prefetch=[
                    qm.Prefetch(
                        query=qm.SparseVector(
                            indices=sparse["indices"], values=sparse["values"]
                        ),
                        using="sparse",
                        limit=limit * 3,
                    ),
                    qm.Prefetch(query=dense, using="dense", limit=limit * 3),
                ],
                query=qm.FusionQuery(fusion=qm.Fusion.RRF),
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            )
        except Exception as e:
            raise VectorStoreError(f"search failed: {e}") from e

        out = []
        for p in results.points:
            payload: dict[str, Any] = p.payload or {}
            out.append(
                {
                    "chunk_id": payload.get("chunk_id"),
                    "doc_id": payload.get("doc_id"),
                    "score": p.score,
                    "payload": payload,
                }
            )
        return out
