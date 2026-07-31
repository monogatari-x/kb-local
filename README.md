# kb-local

本地 RAG 知识库。混合架构:本地嵌入 + 向量检索,云端 LLM 生成。

**AI 原生**:通过 MCP Server,Claude Code / Cursor 可以直接查询你的知识库,无需复制粘贴。

## 当前能力

### 文件类型
- 代码:**PHP / Java / Python / JS / TS / Go** 等 25+ 语言(tree-sitter 语法切片)
- 文档:Markdown(保留标题层级)、PDF(pypdf)、Word/python-docx)、Excel(openpyxl)
- 文本:.txt / .log / .csv / .tsv

### 检索
- BGE-M3 嵌入(中英多语言,稠密 + 稀疏向量)
- Qdrant + SQLite 双库存储,RRF 混合检索
- 可选 bge-reranker-v2-m3 精排(top-20 → top-K)
- 行号引用(`auth.php:10-20 (login)`)

### 接入方式
- **CLI**:`kb add` / `kb search` / `kb watch` / `kb jobs` / `kb status`
- **Web UI**:Vue SPA(搜索 + 文档/切片/任务/监控目录列表),`GET /` serve 自 `frontend/dist/`
- **REST API**:FastAPI,所有 JSON 端点在 `/api/*` 前缀下:`/api/search`、`/api/add`、`/api/status`、`/api/projects`、`/api/documents`、`/api/chunks`、`/api/chunks/{id}`、`/api/watch-dirs`、`/api/jobs`、`/api/health`
- **MCP Server**:Claude Code / Cursor 直接调用 `kb_search` 工具

### 自动化
- 文件监听守护进程(`kb watch start`),文件变化自动重新索引
- 性能基准脚本(`scripts/benchmark.py`)

## 快速开始

### 1. 安装依赖

```bash
make install
```

### 2. 启动 Qdrant

```bash
docker compose up -d qdrant
```

### 3. 初始化数据库

```bash
uv run python scripts/init_db.py
```

### 4. 预下载模型权重(首次约 5GB,~5 分钟)

```bash
uv run python scripts/download_models.py
```

包含 BGE-M3 嵌入(2.4GB) + bge-reranker-v2-m3 精排(2GB)。

### 5. 配置监控目录

编辑 `~/.kb/config.yaml`,或直接用 CLI:

```bash
uv run kb watch add C:/Glow/projects --project dev_projects --strategy first_subdir
```

### 6. 跑首次全量索引

```bash
uv run kb jobs run --type full_scan
```

### 7. 启动文件监听(可选,前台运行)

```bash
uv run kb watch start
```

文件保存后 2 秒内自动重新索引。

### 8. 检索

```bash
# CLI
uv run kb search "用户登录逻辑" --top-k 5
uv run kb search "..." --project myproject --threshold 0.5
uv run kb search "..." --rerank  # 启用 reranker 精排

# Web UI(需先构建前端)
cd frontend && npm install && npm run build && cd ..
uv run python -m kb_api  # 启动 0.0.0.0:8000
# 浏览器打开 http://localhost:8000/

# REST API
curl -X POST http://localhost:8000/api/search -H "Content-Type: application/json" \
  -d '{"query": "用户登录", "top_k": 5}'
```

前端开发模式(Vite 5173 代理到 Python 8000):

```bash
uv run python -m kb_api           # Terminal 1
cd frontend && npm run dev        # Terminal 2,http://localhost:5173/
```

## AI 原生接入(Claude Code / Cursor)

项目根目录已有 `.mcp.json`。在 Claude Code 中:

1. 打开本项目目录
2. Claude Code 自动加载 `.mcp.json`,启动 kb-local MCP server
3. 直接对话:"这个项目的登录逻辑在哪?",Claude Code 自动调 `kb_search` 工具

验证 MCP server 工作:

```bash
uv run python scripts/verify_mcp.py
```

如需全局可用(所有项目),复制到 `~/.claude/mcp.json`:

```json
{
  "mcpServers": {
    "kb-local": {
      "command": "uv",
      "args": ["run", "--directory", "C:/Glow/Projects/kb-local", "python", "-m", "kb_mcp"]
    }
  }
}
```

## 配置

默认 `~/.kb/config.yaml`,可用 `--config` 覆盖:

```bash
uv run --env KB_CONFIG_PATH=/path/to/config.yaml kb search "..."
```

完整字段见 `docs/superpowers/specs/2026-07-22-local-rag-kb-design.md` 第 15 节。

## 测试

```bash
make test                              # 单元测试
make test-int                          # 集成测试(需 Docker)
uv run pytest -m "integration and slow"  # 仅跑 slow + integration
```

## 性能基准

```bash
docker compose up -d qdrant
uv run python scripts/benchmark.py
```

参考数据(MX450 CPU 模式,batch_size=4):
- 100 文件索引:**~540s**(spec <300s,**未达标**,瓶颈在 BGE-M3 CPU 推理)
- 单次检索 avg:**~400ms**(spec <500ms,达标)
- 单次检索 p95:**~500ms**

GPU 加速或跨文件批量嵌入可显著提升索引速度。

## 架构与文档

- 设计文档:`docs/superpowers/specs/2026-07-22-local-rag-kb-design.md`(初版 RAG)、`docs/superpowers/specs/2026-07-29-kb-api-webui-enhancement-design.md`(Web UI 增强)
- 实施计划:`docs/superpowers/plans/2026-07-22-local-rag-kb-mvp.md`、`docs/superpowers/plans/2026-07-29-kb-api-webui-enhancement.md`

## 硬件建议

- CPU 模式:i5 及以上,16GB 内存可跑(慢)
- GPU 加速:可选,需 4GB+ 可用显存
