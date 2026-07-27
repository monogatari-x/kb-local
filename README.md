# kb-local

本地 RAG 知识库（MVP）。混合架构：本地嵌入 + 向量检索，云端 LLM 生成。

## 当前能力（MVP）

- 支持 PHP / Java / Python / JS / TS / Go 等 25+ 语言的代码语法切片（tree-sitter）
- 支持 Markdown（保留标题层级 + 代码块完整）
- 支持纯文本（.txt/.log/.csv/.tsv）
- BGE-M3 嵌入（中英多语言，稠密 + 稀疏向量）
- Qdrant + SQLite 双库存储
- 混合检索（RRF 融合），带行号引用
- CLI 工具：`kb add` / `kb search` / `kb watch` / `kb jobs` / `kb status`

> 阶段 2 才支持：PDF/Word/Excel/PPT、OCR、Reranker、MCP Server、REST API、Web UI

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

### 4. 预下载模型权重（首次约 2.4GB）

```bash
uv run python scripts/download_models.py
```

### 5. 配置监控目录

编辑 `~/.kb/config.yaml`，或直接用 CLI：

```bash
uv run kb watch add C:/Glow/projects --project dev_projects --strategy first_subdir
```

### 6. 跑首次全量索引

```bash
uv run kb jobs run --type full_scan
```

### 7. 检索

```bash
uv run kb search "用户登录"
```

## 配置

默认配置在 `~/.kb/config.yaml`，可用 `--config` 覆盖：

```bash
uv run --env KB_CONFIG_PATH=/path/to/config.yaml kb search "..."
```

完整字段见 `docs/superpowers/specs/2026-07-22-local-rag-kb-design.md` 第 15 节。

## 测试

```bash
make test          # 单元测试
make test-int      # 集成测试（需 Docker）
```

## 架构与文档

- 设计文档：`docs/superpowers/specs/2026-07-22-local-rag-kb-design.md`
- 实施计划：`docs/superpowers/plans/2026-07-22-local-rag-kb-mvp.md`

## 硬件建议

- CPU 模式：i5 及以上，16GB 内存可跑
- GPU 加速：可选，需 4GB+ 可用显存（本机 MX450 默认走 CPU）
