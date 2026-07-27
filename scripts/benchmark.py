"""性能基准:验证 MVP 是否满足 spec 验收标准。

用法:
    uv run python scripts/benchmark.py [--sample-size 100] [--json]
"""

import contextlib
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import typer
from rich.console import Console
from rich.table import Table

from kb_core.chunkers.code_chunker import CodeChunker
from kb_core.chunkers.markdown_chunker import MarkdownChunker
from kb_core.chunkers.recursive_chunker import RecursiveChunker
from kb_core.embeddings.bge_m3 import BGE_M3_EMBEDDER
from kb_core.loaders.code_loader import CodeLoader
from kb_core.loaders.markdown_loader import MarkdownLoader
from kb_core.loaders.registry import LoaderRegistry
from kb_core.loaders.text_loader import TextLoader
from kb_core.pipelines.indexing import IndexingPipeline
from kb_core.pipelines.retrieval import RetrievalPipeline
from kb_core.stores.qdrant_store import QdrantStore
from kb_core.stores.sqlite_store import SQLiteStore

console = Console()

SAMPLE_QUERIES = ["用户登录", "认证逻辑", "密码策略", "session 处理", "权限检查"]


def _generate_sample(target: Path, idx: int, kind: str) -> Path:
    if kind == "php":
        path = target / f"sample_{idx:03d}.php"
        path.write_text(
            f"""<?php
class Service{idx} {{
    public function authenticate($user, $password) {{
        if ($this->verify($user, $password)) {{
            return $this->createSession($user);
        }}
        return false;
    }}

    private function verify($u, $p) {{
        return password_verify($p, $this->getHash($u));
    }}

    public function login($username, $password) {{
        $result = $this->authenticate($username, $password);
        if ($result) {{
            $this->logLogin($username);
        }}
        return $result;
    }}
}}
""",
            encoding="utf-8",
        )
    elif kind == "md":
        path = target / f"doc_{idx:03d}.md"
        path.write_text(
            f"""# 设计文档 #{idx}

## 用户登录

系统使用 LDAP 账号登录。失败 5 次锁定 30 分钟。

## 密码策略

密码至少 12 位,含大小写 + 数字 + 符号。每 90 天强制更换。

## 权限模型

采用 RBAC,角色:admin / editor / viewer。
""",
            encoding="utf-8",
        )
    else:
        path = target / f"note_{idx:03d}.txt"
        path.write_text(
            f"""会议纪要 #{idx}

讨论了认证流程的优化方案。
session 过期时间从 30 分钟调整到 2 小时。
密码强度校验由前端迁到后端统一处理。
""",
            encoding="utf-8",
        )
    return path


def _generate_samples(target: Path, n: int) -> list[Path]:
    files: list[Path] = []
    for i in range(n):
        r = i % 10
        if r < 5:
            kind = "php"
        elif r < 8:
            kind = "md"
        else:
            kind = "txt"
        files.append(_generate_sample(target, i, kind))
    return files


def main(
    sample_size: int = typer.Option(100, "--sample-size", help="样本文件数"),
    collection: str = typer.Option("kb_benchmark", "--collection", help="Qdrant collection 名"),
    json_output: bool = typer.Option(False, "--json", help="JSON 输出"),
) -> None:
    tmp = Path(tempfile.mkdtemp(prefix="kb_bench_"))
    sqlite_path = tmp / "bench.db"
    store = SQLiteStore(sqlite_path)
    store.init_schema()

    qdrant = QdrantStore(url="http://localhost:6333", collection=collection)
    try:
        with contextlib.suppress(Exception):
            qdrant.client.delete_collection(collection)
        qdrant.ensure_collection()
    except Exception as e:
        console.print(f"[red]Qdrant 不可用: {e}. 请先 docker compose up -d qdrant[/red]")
        raise typer.Exit(code=2) from e

    reg = LoaderRegistry()
    reg.register(CodeLoader())
    reg.register(MarkdownLoader())
    reg.register(TextLoader())

    embedder = BGE_M3_EMBEDDER(device="cpu", batch_size=4)
    chunkers = {"code": CodeChunker(), "markdown": MarkdownChunker(), "text": RecursiveChunker()}
    indexing = IndexingPipeline(store, qdrant, reg, embedder, chunkers)
    retrieval = RetrievalPipeline(store, qdrant, embedder)

    src_dir = tmp / "src"
    src_dir.mkdir()
    files = _generate_samples(src_dir, sample_size)

    t0 = time.perf_counter()
    for f in files:
        indexing.index_file(
            f,
            watch_dir=src_dir,
            project_strategy="first_subdir",
            project_name="bench",
        )
    index_time = time.perf_counter() - t0

    latencies_ms: list[float] = []
    for q in SAMPLE_QUERIES:
        t0 = time.perf_counter()
        retrieval.search(q, top_k=5)
        latencies_ms.append((time.perf_counter() - t0) * 1000)
    avg_latency_ms = statistics.mean(latencies_ms)
    p95_latency_ms = (
        statistics.quantiles(latencies_ms, n=20)[-1] if len(latencies_ms) >= 2 else avg_latency_ms
    )

    index_spec_pass = index_time < 300
    search_spec_pass = avg_latency_ms < 500

    if json_output:
        import json

        console.print_json(
            json.dumps(
                {
                    "sample_size": sample_size,
                    "index_total_s": round(index_time, 2),
                    "index_per_file_s": round(index_time / sample_size, 3),
                    "index_spec_pass": index_spec_pass,
                    "search_avg_ms": round(avg_latency_ms, 1),
                    "search_p95_ms": round(p95_latency_ms, 1),
                    "search_spec_pass": search_spec_pass,
                },
                ensure_ascii=False,
            )
        )
    else:
        table = Table(title="性能基准", show_header=False)
        table.add_row("样本数", str(sample_size))
        table.add_row(
            "索引总耗时",
            f"{index_time:.1f}s  ({index_time / sample_size:.2f}s/文件)",
        )
        table.add_row(
            "索引 spec (<5min/100)",
            "[green]PASS[/green]" if index_spec_pass else "[red]FAIL[/red]",
        )
        table.add_row("检索 avg 延迟", f"{avg_latency_ms:.0f}ms")
        table.add_row("检索 p95 延迟", f"{p95_latency_ms:.0f}ms")
        table.add_row(
            "检索 spec (<500ms)",
            "[green]PASS[/green]" if search_spec_pass else "[red]FAIL[/red]",
        )
        console.print(table)

    store.close()


if __name__ == "__main__":
    typer.run(main)
