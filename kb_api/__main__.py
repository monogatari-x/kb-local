"""启动 uvicorn API server。

用法:
    uv run python -m kb_api [--host 0.0.0.0] [--port 8000]
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import typer
import uvicorn


def main(
    host: str = typer.Option("0.0.0.0", "--host"),
    port: int = typer.Option(8000, "--port"),
    reload: bool = typer.Option(False, "--reload"),
) -> None:
    dist = Path(__file__).parent.parent / "frontend" / "dist"
    if not dist.is_dir():
        sys.stderr.write(
            "[kb-api] WARNING: frontend/dist not found. "
            "Run `cd frontend && npm run build` to enable Vue UI; "
            "otherwise HTTP / will return 404.\n"
        )
    uvicorn.run(
        "kb_api.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    typer.run(main)
