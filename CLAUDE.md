# CLAUDE.md

This file gives Claude Code (and other AI agents) context about this project.

## What is kb-local

本地 RAG 知识库。文件 → 切片 → 嵌入(BGE-M3)→ 存储(SQLite + Qdrant)→ 混合检索。混合架构:本地推理 + 云端 LLM 生成。

主要语言:Python 3.12。框架:Typer (CLI)、FastAPI (REST)、MCP Python SDK (AI 工具)。

## 项目结构

```
kb_core/      核心库(models / config / stores / loaders / chunkers / embeddings / pipelines)
kb_cli/       CLI 实现(Typer)
kb_api/       REST API(FastAPI)
kb_mcp/       MCP Server(供 Claude Code / Cursor 调用)
scripts/      运维脚本(init_db / download_models / benchmark / verify_mcp)
tests/        unit + integration(标记:integration / slow)
```

## 如何使用本项目知识库(AI 必读)

当你(Claude Code)在本项目或加载了 kb-local MCP server 的任何项目里:

1. **优先用 `kb_search` 工具查代码**,而不是 grep。语义检索比文本匹配强很多。
   - 例:用户问"用户登录逻辑在哪" → 直接调 `kb_search(query="用户登录认证")`,不要 grep "login"
   - 例:用户问"X 功能怎么实现" → 先 `kb_search(query="X 功能")` 再读返回的代码块

2. **`kb_search` 返回带行号引用**(`auth.py:10-20 (login)`),引用时直接给路径 + 行号。

3. **空结果时不要反复试**:返回"未找到"就是真的没索引到。提示用户运行 `kb jobs run` 或检查 `kb watch list`。

4. **不要用 `kb_search` 查本项目源码**:本项目代码就在你眼前,直接 Read 即可。`kb_search` 用于查"被索引的外部项目"(用户的 dev projects)。

5. **`kb_status` 工具**:用户问"知识库有多少文件" / "索引是否最新" → 调 `kb_status`。

## 编码约定(本项目)

- **无注释**:不在生产代码里写注释。注释只在测试或脚本中,且仅解释 WHY(非 WHAT)。
- **类型标注必填**:mypy strict=true。函数签名必须有完整类型,包括返回值。
- **ruff 规则**:`E/F/I/N/UP/B/SIM`。`line-length=100`。
- **B008 例外**:`typer.Argument` / `typer.Option` 已在 pyproject.toml 加入 `extend-immutable-calls`。
- **commit 前缀**:`feat:` / `fix:` / `docs:` / `test:` / `refactor:`。
- **TDD 流程**:RED(看测试失败)→ GREEN(最小实现)→ REFACTOR。先写测试再写代码。

## 常用命令

```bash
# 测试
make test                                    # 单元
make test-int                                # 集成(需要 Docker)
HF_HUB_OFFLINE=1 uv run pytest -m "slow"     # slow 测试需要 HF_HUB_OFFLINE=1

# 质量检查
uv run ruff check .
uv run ruff format .
uv run mypy kb_core/ kb_cli/ kb_api/ kb_mcp/

# 启动服务
docker compose up -d qdrant                  # Qdrant 向量库
uv run python -m kb_api                      # REST API :8000
uv run python -m kb_mcp                      # MCP server (stdio)
uv run kb watch start                        # 文件监听守护进程

# 数据初始化(首次)
uv run python scripts/init_db.py
uv run python scripts/download_models.py     # ~5GB,首次约 5 分钟
```

## 关键依赖版本锁定

- `tree-sitter>=0.21,<0.22`(不能升级,`tree_sitter_languages` 锁死了)
- `transformers>=4.40,<5`(FlagEmbedding reranker 不兼容 transformers 5.x)
- `qdrant-client>=1.10`(测试用 testcontainer 1.10.1,有版本警告但可工作)

## 性能特征(诚实评估)

- 索引速度:CPU 模式 ~5-8s/文件。100 文件 5-10 分钟。瓶颈在 BGE-M3 推理。
- 检索延迟:avg 400ms,p95 500ms。达到 spec <500ms。
- BGE-M3 模型大小:2.4GB(首次下载慢,CN 网络需 `HF_ENDPOINT=https://hf-mirror.com`)。

## 已知问题

- `tree_sitter_languages` 已废弃,产生 FutureWarning(不阻塞)
- qdrant testcontainer 版本(1.10.1)与 client(1.18)有版本警告
- 文件监听守护进程目前是前台运行,需要 nohup / 任务计划程序后台化
- Windows 上 HF cache 不支持 symlink,会有警告(不影响功能)

## 不要做的事

- 不要删除 `config/qdrant.yaml` 中的 `default_segment_number`,Qdrant 1.10.1 启动需要它
- 不要给 `_state` 字典加锁,MCP server 是单线程 asyncio
- 不要在测试中真实下载模型,用 `monkeypatch` 或 `unittest.mock`
- 不要把 `.superpowers/sdd/` 加入 git,那是本地工作目录(gitignored)
