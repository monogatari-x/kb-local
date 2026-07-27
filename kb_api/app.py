"""kb-local REST API:FastAPI 应用工厂。

用法:
    uv run python -m kb_api  # 启动 0.0.0.0:8000
"""

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from kb_core.config import Settings as KBSettings
from kb_core.config import load_settings
from kb_core.pipelines.retrieval import RetrievalPipeline
from kb_core.stores.sqlite_store import SQLiteStore


class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    project: str | None = None
    threshold: float = 0.3
    rerank: bool = False


class AddRequest(BaseModel):
    path: str
    project: str = "manual"
    strategy: str = "fixed"


def create_app(
    store: SQLiteStore | None = None,
    settings: KBSettings | None = None,
    bootstrap_pipeline: bool = True,
    retrieval: RetrievalPipeline | None = None,
    pipeline: Any = None,
) -> FastAPI:
    app = FastAPI(title="kb-local API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if settings is None:
        settings = load_settings(None)
    if store is None:
        sqlite_path = Path(settings.database.sqlite_path).expanduser()
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        store = SQLiteStore(sqlite_path, check_same_thread=False)
        store.init_schema()

    if bootstrap_pipeline and (retrieval is None or pipeline is None):
        from kb_cli.commands.jobs import _build_pipeline

        pipeline = _build_pipeline(store, settings)
        retrieval = RetrievalPipeline(
            store,
            pipeline.qdrant_store,
            pipeline.embedder,
            reranker=None,
        )

    app.state.store = store
    app.state.settings = settings
    app.state.retrieval = retrieval
    app.state.pipeline = pipeline

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/status")
    def status() -> dict[str, int]:
        s: SQLiteStore = app.state.store
        docs = s.conn.execute(
            "SELECT COUNT(*) FROM documents WHERE status = 'active'"
        ).fetchone()[0]
        chunks = s.conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        watch_dirs = s.conn.execute("SELECT COUNT(*) FROM watch_dirs").fetchone()[0]
        jobs = s.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        return {
            "documents": docs,
            "chunks": chunks,
            "watch_dirs": watch_dirs,
            "jobs": jobs,
        }

    @app.post("/search")
    def search(req: SearchRequest) -> dict[str, list[dict[str, Any]]]:
        if app.state.retrieval is None:
            raise HTTPException(status_code=503, detail="retrieval pipeline not bootstrapped")
        filters: dict[str, Any] | None = None
        if req.project:
            filters = {"must": [{"key": "project", "match": {"value": req.project}}]}
        results = app.state.retrieval.search(
            req.query,
            top_k=req.top_k,
            filters=filters,
            score_threshold=req.threshold,
            rerank=req.rerank,
        )
        return {
            "results": [
                {
                    "text": r.chunk.text,
                    "citation": r.citation,
                    "score": r.final_score,
                    "chunk_type": r.chunk.chunk_type.value,
                    "project": r.document.project if r.document else None,
                }
                for r in results
            ]
        }

    @app.post("/add")
    def add(req: AddRequest) -> dict[str, str]:
        if app.state.pipeline is None:
            raise HTTPException(status_code=503, detail="indexing pipeline not bootstrapped")
        path = Path(req.path)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"file not found: {path}")
        try:
            doc_id = app.state.pipeline.index_file(
                path,
                watch_dir=path.parent,
                project_strategy=req.strategy,
                project_name=req.project,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
        return {"doc_id": doc_id}

    return app
