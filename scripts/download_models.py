"""预下载 BGE-M3 模型权重。

用法:
    uv run python scripts/download_models.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import typer
from rich.console import Console

console = Console()


def main(
    model: str = typer.Option("BAAI/bge-m3", "--model"),
    cache_dir: str = typer.Option(None, "--cache-dir", envvar="HF_HOME"),
) -> None:
    if cache_dir:
        os.environ["HF_HOME"] = cache_dir
        console.print(f"[dim]HF_HOME={cache_dir}[/dim]")

    console.print(f"[blue]下载[/blue] {model}（约 2.4GB，请耐心等待）...")
    from FlagEmbedding import BGEM3FlagModel

    BGEM3FlagModel(model, use_fp16=False)
    console.print(f"[green]OK[/green] {model} 已就绪")


if __name__ == "__main__":
    typer.run(main)
