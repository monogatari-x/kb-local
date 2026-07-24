from kb_core.embeddings.bge_m3 import BGE_M3_EMBEDDER
from kb_core.models import Chunk, Document, SearchResult
from kb_core.stores.qdrant_store import QdrantStore
from kb_core.stores.sqlite_store import SQLiteStore


class RetrievalPipeline:
    def __init__(
        self,
        sqlite_store: SQLiteStore,
        qdrant_store: QdrantStore,
        embedder: BGE_M3_EMBEDDER,
    ) -> None:
        self.sqlite_store = sqlite_store
        self.qdrant_store = qdrant_store
        self.embedder = embedder

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: dict[str, object] | None = None,
        score_threshold: float = 0.3,
    ) -> list[SearchResult]:
        dense, sparse = self.embedder.embed_query(query)
        raw = self.qdrant_store.search_dense_sparse(
            dense=dense,
            sparse=sparse,
            filters=filters,
            limit=max(top_k * 3, 30),
        )
        raw = [r for r in raw if r["score"] >= score_threshold][:top_k]
        results: list[SearchResult] = []
        for r in raw:
            chunk = self.sqlite_store.get_chunk(r["chunk_id"])
            if chunk is None:
                continue
            doc = self.sqlite_store.get_document(r["doc_id"])
            citation = self._build_citation(chunk, doc)
            prev_c, next_c = self.sqlite_store.get_neighbor_chunk_ids(chunk.chunk_id)
            results.append(SearchResult(
                chunk=chunk,
                document=doc,
                final_score=r["score"],
                vector_score=r["score"],
                rerank_score=0.0,
                citation=citation,
                highlights=[],
                prev_chunk_id=prev_c,
                next_chunk_id=next_c,
            ))
        return results

    @staticmethod
    def _build_citation(chunk: Chunk, doc: Document | None) -> str:
        if doc is None:
            return chunk.chunk_id
        lines = f":{chunk.start_line}-{chunk.end_line}" if chunk.start_line else ""
        sym = f" ({chunk.symbol_path})" if chunk.symbol_path else ""
        return f"{doc.rel_path}{lines}{sym}"
