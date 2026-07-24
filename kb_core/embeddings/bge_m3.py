from typing import Any

from kb_core.embeddings.cache import EmbeddingCache
from kb_core.embeddings.device import resolve_device
from kb_core.exceptions import EmbeddingError, ModelLoadError
from kb_core.utils.hashing import content_hash


class BGE_M3_EMBEDDER:
    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        device: str = "auto",
        cache: EmbeddingCache | None = None,
        batch_size: int | None = None,
    ) -> None:
        self.model_name = model_name
        self.cache = cache
        self.device = resolve_device(device)
        self.batch_size = batch_size or (4 if self.device == "cuda" else 16)
        try:
            from FlagEmbedding import BGEM3FlagModel

            self._model = BGEM3FlagModel(
                model_name,
                use_fp16=(self.device == "cuda"),
                device=self.device,
            )
        except Exception as e:
            raise ModelLoadError(f"Failed to load BGE-M3: {e}") from e

    def vector_size(self) -> int:
        return 1024

    def embed_texts(
        self, texts: list[str]
    ) -> tuple[list[list[float]], list[dict[str, Any]]]:
        if not texts:
            return [], []

        miss_idx: list[int] = []
        miss_texts: list[str] = []
        dense_out: dict[int, list[float]] = {}
        sparse_out: dict[int, dict[str, Any]] = {}

        if self.cache is not None:
            for i, t in enumerate(texts):
                cached = self.cache.get(content_hash(t))
                if cached is not None:
                    d, s = cached
                    dense_out[i] = d
                    sparse_out[i] = s
                else:
                    miss_idx.append(i)
                    miss_texts.append(t)
        else:
            miss_idx = list(range(len(texts)))
            miss_texts = list(texts)

        if miss_texts:
            try:
                result = self._model.encode(
                    miss_texts,
                    batch_size=self.batch_size,
                    return_dense=True,
                    return_sparse=True,
                    return_colbert_vecs=False,
                )
            except Exception as e:
                raise EmbeddingError(f"BGE-M3 encode failed: {e}") from e
            dense_vecs = result["dense_vecs"]
            sparse_vecs = result["lexical_weights"]
            for j, i in enumerate(miss_idx):
                d = dense_vecs[j].tolist()
                s = {
                    "indices": [int(k) for k in sparse_vecs[j]],
                    "values": [float(v) for v in sparse_vecs[j].values()],
                }
                dense_out[i] = d
                sparse_out[i] = s
                if self.cache is not None:
                    self.cache.put(content_hash(miss_texts[j]), d, s)

        return (
            [dense_out[i] for i in range(len(texts))],
            [sparse_out[i] for i in range(len(texts))],
        )

    def embed_query(self, text: str) -> tuple[list[float], dict[str, Any]]:
        dense, sparse = self.embed_texts([text])
        return dense[0], sparse[0]
