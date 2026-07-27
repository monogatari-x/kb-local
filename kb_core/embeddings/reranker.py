"""bge-reranker-v2-m3 精排包装。"""

from FlagEmbedding import FlagReranker


class Reranker:
    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        use_fp16: bool = False,
    ) -> None:
        self.model_name = model_name
        self.model = FlagReranker(model_name, use_fp16=use_fp16)

    def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int | None = None,
    ) -> list[tuple[int, float]]:
        if not documents:
            return []
        pairs = [[query, d] for d in documents]
        scores = self.model.compute_score(pairs, normalize=True)
        if not isinstance(scores, list):
            scores = [scores]
        indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return indexed if top_k is None else indexed[:top_k]
