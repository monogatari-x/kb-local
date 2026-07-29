"""kb-local REST API:FastAPI 应用工厂。

用法:
    uv run python -m kb_api  # 启动 0.0.0.0:8000
"""

from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from kb_core.config import Settings as KBSettings
from kb_core.config import load_settings
from kb_core.pipelines.retrieval import RetrievalPipeline
from kb_core.stores.sqlite_store import SQLiteStore

STATIC_DIR = Path(__file__).parent / "static"


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


class DocumentsRequest(BaseModel):
    project: str | None = None
    status: str | None = None
    q: str | None = None
    sort: Literal["ingested_at", "size_bytes", "project", "file_type"] = "ingested_at"
    order: Literal["asc", "desc"] = "desc"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


class ChunksListRequest(BaseModel):
    doc_id: str | None = None
    project: str | None = None
    chunk_type: (
        Literal[
            "paragraph",
            "heading",
            "code_function",
            "code_class",
            "code_statement",
            "table",
            "list",
            "image_caption",
            "mixed",
        ]
        | None
    ) = None
    q: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


class JobsRequest(BaseModel):
    status: str | None = None
    limit: int = Field(default=50, ge=1, le=500)


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

    if STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    api_router = APIRouter(prefix="/api")

    @api_router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @api_router.get("/status")
    def status() -> dict[str, int]:
        s: SQLiteStore = app.state.store
        docs = s.conn.execute("SELECT COUNT(*) FROM documents WHERE status = 'active'").fetchone()[
            0
        ]
        chunks = s.conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        watch_dirs = s.conn.execute("SELECT COUNT(*) FROM watch_dirs").fetchone()[0]
        jobs = s.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        return {
            "documents": docs,
            "chunks": chunks,
            "watch_dirs": watch_dirs,
            "jobs": jobs,
        }

    @api_router.get("/projects")
    def projects() -> dict[str, list[str]]:
        s: SQLiteStore = app.state.store
        rows = s.conn.execute(
            "SELECT DISTINCT project FROM documents WHERE status = 'active' ORDER BY project"
        ).fetchall()
        return {"projects": [r["project"] for r in rows]}

    @api_router.get("/documents")
    def documents(req: DocumentsRequest = Depends()) -> dict[str, Any]:
        s: SQLiteStore = app.state.store
        where = []
        params: list[Any] = []
        if req.project:
            where.append("project = ?")
            params.append(req.project)
        if req.status:
            where.append("status = ?")
            params.append(req.status)
        if req.q:
            where.append("(rel_path LIKE ? OR source_path LIKE ?)")
            like = f"%{req.q}%"
            params.extend([like, like])
        where_clause = (" WHERE " + " AND ".join(where)) if where else ""

        total = s.conn.execute(f"SELECT COUNT(*) FROM documents{where_clause}", params).fetchone()[
            0
        ]

        offset = (req.page - 1) * req.page_size
        rows = s.conn.execute(
            f"SELECT doc_id, source_path, rel_path, project, file_type, language, "
            f"size_bytes, ingested_at, indexed_at, status "
            f"FROM documents{where_clause} "
            f"ORDER BY {req.sort} {req.order.upper()} LIMIT ? OFFSET ?",
            [*params, req.page_size, offset],
        ).fetchall()

        return {
            "items": [dict(r) for r in rows],
            "total": total,
            "page": req.page,
            "page_size": req.page_size,
        }

    @api_router.get("/chunks")
    def list_chunks(req: ChunksListRequest = Depends()) -> dict[str, Any]:
        s: SQLiteStore = app.state.store
        where = []
        params: list[Any] = []
        if req.doc_id:
            where.append("c.doc_id = ?")
            params.append(req.doc_id)
        if req.project:
            where.append("d.project = ?")
            params.append(req.project)
        if req.chunk_type:
            where.append("c.chunk_type = ?")
            params.append(req.chunk_type)
        if req.q:
            where.append("c.text_truncated LIKE ?")
            params.append(f"%{req.q}%")
        where_clause = (" WHERE " + " AND ".join(where)) if where else ""

        total = s.conn.execute(
            f"SELECT COUNT(*) FROM chunks c LEFT JOIN documents d "
            f"ON c.doc_id = d.doc_id{where_clause}",
            params,
        ).fetchone()[0]

        offset = (req.page - 1) * req.page_size
        rows = s.conn.execute(
            f"SELECT c.chunk_id, c.doc_id, c.chunk_type, c.text_truncated, "
            f"c.start_line, c.end_line, c.language, c.ordinal "
            f"FROM chunks c LEFT JOIN documents d ON c.doc_id = d.doc_id "
            f"{where_clause} ORDER BY c.doc_id, c.ordinal "
            f"LIMIT ? OFFSET ?",
            [*params, req.page_size, offset],
        ).fetchall()

        return {
            "items": [dict(r) for r in rows],
            "total": total,
            "page": req.page,
            "page_size": req.page_size,
        }

    @api_router.get("/chunks/{chunk_id}")
    def get_chunk(chunk_id: str) -> dict[str, Any]:
        s: SQLiteStore = app.state.store
        row = s.conn.execute(
            "SELECT chunk_id, doc_id, chunk_type, text, start_line, end_line, "
            "language, section_path, symbol_path FROM chunks WHERE chunk_id = ?",
            (chunk_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"chunk not found: {chunk_id}")
        return dict(row)

    @api_router.get("/watch-dirs")
    def watch_dirs() -> dict[str, Any]:
        s: SQLiteStore = app.state.store
        rows = s.conn.execute(
            "SELECT id, path, project_name, project_strategy, recursive, "
            "file_types, exclude_patterns, include_patterns, created_at, last_scan_at "
            "FROM watch_dirs ORDER BY id"
        ).fetchall()
        return {"items": [dict(r) for r in rows]}

    @api_router.get("/jobs")
    def jobs(req: JobsRequest = Depends()) -> dict[str, Any]:
        s: SQLiteStore = app.state.store
        if req.status:
            rows = s.conn.execute(
                "SELECT job_id, type, status, started_at, finished_at, "
                "total_files, processed_files, failed_files, error_log, trigger "
                "FROM jobs WHERE status = ? ORDER BY started_at DESC LIMIT ?",
                (req.status, req.limit),
            ).fetchall()
        else:
            rows = s.conn.execute(
                "SELECT job_id, type, status, started_at, finished_at, "
                "total_files, processed_files, failed_files, error_log, trigger "
                "FROM jobs ORDER BY started_at DESC LIMIT ?",
                (req.limit,),
            ).fetchall()
        return {"items": [dict(r) for r in rows]}

    @api_router.post("/search")
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
                    "chunk_id": r.chunk.chunk_id,
                }
                for r in results
            ]
        }

    @api_router.post("/add")
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

    app.include_router(api_router)

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html", media_type="text/html")

    return app
