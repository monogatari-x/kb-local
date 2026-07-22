# kb-local

本地 RAG 知识库。混合架构：本地嵌入 + 向量检索，云端 LLM 生成。

## 快速开始

```bash
make install
uv run python scripts/init_db.py
uv run python scripts/download_models.py
uv run kb --help
```

详见 `docs/superpowers/specs/2026-07-22-local-rag-kb-design.md`。
