# kb-local Web UI 增强 · 设计文档

- 日期:2026-07-29
- 状态:已通过用户评审,准备进入实施计划阶段
- 目标读者:实施阶段的 AI / 开发者

## 1. 背景与目标

现有 `kb_api/static/index.html` 是一个单文件 SPA,只有搜索框和状态栏。用户希望:

1. 顶栏的"文档 / 切片 / 监控目录 / 任务"四个数字可点,跳到对应列表页查看详情。
2. 整体界面更丰富,使用现代前端框架(Vue 3 + Vite + TypeScript + Vue Router)。
3. 保留现有深色主题(`#0f1115` / `#161a22` / `#1c2129`,accent `#5b9cff`)。

约束:
- 不影响 MCP server 和 CLI(它们不通过 HTTP 调用 `kb_api`,已通过 grep 验证)。
- 后端不动核心逻辑,只新增只读列表端点。
- 列表页只读,不带任何操作按钮(用户明确要求)。

## 2. 目录结构

`frontend/` 作为独立 Vue 项目,与 `kb_api/` 平级。开发时 Vite 跑 5173 代理到 Python 8000;生产时 Python 通过 `StaticFiles` 直接 serve `frontend/dist`。

```
kb-local/
├── kb_api/
│   ├── app.py                # FastAPI 应用工厂,所有端点加 /api 前缀
│   ├── __main__.py
│   └── static/               # (生产)由 frontend/dist 拷贝或直接 mount
├── frontend/                 # 新增:独立 Vue + Vite 项目
│   ├── package.json
│   ├── vite.config.ts        # proxy: { '/api': 'http://localhost:8000' }
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.ts
│       ├── App.vue
│       ├── router.ts
│       ├── api.ts            # 统一 fetch 包装
│       ├── components/
│       │   ├── NavBar.vue
│       │   ├── StatusBar.vue
│       │   ├── Pagination.vue
│       │   ├── StatusBadge.vue
│       │   ├── ScoreBadge.vue
│       │   └── CodeBlock.vue
│       └── views/
│           ├── SearchView.vue
│           ├── DocumentsView.vue
│           ├── ChunksView.vue
│           ├── WatchDirsView.vue
│           └── JobsView.vue
└── tests/
    └── unit/
        ├── test_api.py       # 扩展:新增端点的单测
        └── test_api_legacy.py # (可选)验证老路径移除
```

生产部署:
- `kb_api/app.py` 检查 `STATIC_DIR = frontend/dist`(优先)或 `kb_api/static`(回退)
- mount `StaticFiles(directory=STATIC_DIR, html=True)` 到 `/`
- SPA fallback 通过 `StaticFiles(html=True)` 内置能力实现:`html=True` 会自动把 404 路径回落到 `index.html`,无需手写 catch-all 路由
- `kb_api/__main__.py` 启动时如果 `frontend/dist` 不存在,stderr 输出警告并提示跑 `cd frontend && npm run build`

## 3. 后端 API 设计

### 3.1 路径前缀

所有现有端点统一加 `/api` 前缀:

| 旧路径            | 新路径             |
|-------------------|--------------------|
| `GET /health`     | `GET /api/health`  |
| `GET /status`     | `GET /api/status`  |
| `GET /projects`   | `GET /api/projects`|
| `POST /search`    | `POST /api/search` |
| `POST /add`       | `POST /api/add`    |

`GET /` 仍返回 SPA 入口(不进 `/api` 前缀)。

MCP server (`kb_mcp/server.py`) 和 CLI (`kb_cli/`) 都不通过 HTTP 调 `kb_api`,本次重构对它们零影响。

### 3.2 新增只读端点

```
GET /api/documents
    ?project=&status=&q=&sort=ingested_at&order=desc&page=1&page_size=50
    -> { items: [{doc_id, source_path, rel_path, project, file_type, language,
                  size_bytes, ingested_at, indexed_at, status}],
         total, page, page_size }

GET /api/chunks
    ?doc_id=&project=&chunk_type=&q=&page=1&page_size=50
    -> { items: [{chunk_id, doc_id, chunk_type, citation, text_truncated,
                  start_line, end_line, language}],
         total, page, page_size }

GET /api/chunks/{chunk_id}
    -> { chunk_id, doc_id, chunk_type, text, citation, start_line, end_line,
         language, parser_version, embedding_version }

GET /api/watch-dirs
    -> { items: [{dir_id, path, project_strategy, enabled, last_scanned_at}] }

GET /api/jobs
    ?status=&type=&limit=50
    -> { items: [{job_id, type, status, started_at, finished_at,
                  docs_affected, error_msg}] }
```

返回格式约定:列表端点统一 `{items, total, page, page_size}`;详情端点直接返回对象。

`text_truncated` 字段是 `text` 的前 N 字符(暂定 500),用于列表视图;完整文本走 `/api/chunks/{id}` 按需加载。

### 3.3 实现要点

- 所有列表查询直接在 `SQLiteStore` 上用 `conn.execute()` 加参数化 LIMIT/OFFSET,不引入新 ORM。
- `sort` 字段使用白名单校验(只允许 `ingested_at|size_bytes|project|file_type`),避免 SQL 注入。
- 复用现有 `app.state.store` / `app.state.settings`,不新增依赖。

## 4. 前端架构

### 4.1 路由

vue-router history 模式,5 个路由:

```
/                -> SearchView (默认页)
/documents       -> DocumentsView
/chunks          -> ChunksView
/watch-dirs      -> WatchDirsView
/jobs            -> JobsView
/:pathMatch(.*)  -> NotFoundView
```

历史模式需要后端配合:Python 在 mount 静态资源时,对未匹配 `/api/*` 的所有路径都返回 `index.html`(SPA fallback)。

### 4.2 状态管理

**不用 Pinia**(YAGNI)。每个 View 自己持有列表数据 + 过滤状态,通过 URL query string 持久化:

```
/documents?project=yaf&status=active&q=login&page=2
```

刷新页面或分享链接都能恢复筛选状态。

### 4.3 关键交互

**搜索结果卡片:**
- 默认显示前 500 字符 + "显示更多"折叠
- 右侧"查看完整切片"按钮 → `GET /api/chunks/{chunk_id}` → Modal 展示全文 + 元信息
- 卡片底部"跳转到文档"链接 → `/documents?doc_id=xxx`

**文档列表行:**
- 默认按 `ingested_at desc`
- 行内展开(inline expand):点击行展开,异步加载该文档下的切片摘要(`GET /api/chunks?doc_id=xxx&page_size=20`)

**切片列表行:**
- 默认显示 `text_truncated` + 元信息(citation、chunk_type)
- 点击行 → 弹 Modal 显示全文(`GET /api/chunks/{chunk_id}`)

**监控目录 / 任务:**
- 纯只读表格,无操作按钮

**状态栏(右上角):**
- 四个数字 `文档 / 切片 / 监控目录 / 任务` 均可点 → 跳转到对应列表页

### 4.4 样式

复用现有深色主题 CSS 变量。把 `kb_api/static/index.html` 里的 `:root` 变量原样搬到 `frontend/src/assets/theme.css`,组件用 scoped style + `var(--xxx)` 引用。

## 5. 数据流

### 5.1 搜索流程

1. 用户在 `/` 输入查询 → `POST /api/search`
2. 后端走 `RetrievalPipeline.search()`,返回 `text/citation/score/chunk_type/project/chunk_id`
3. 前端展示卡片,长文本默认折叠到 ~500 字符
4. 点击"查看完整切片" → `GET /api/chunks/{chunk_id}` → Modal
5. 点击"跳转到文档" → `/documents?doc_id=xxx`

### 5.2 列表流程

1. 进入 `/documents` → `GET /api/documents?sort=ingested_at&order=desc&page=1`
2. 修改过滤器 → 同步到 URL query string → 重新请求
3. 点击行 → 行内展开 + `GET /api/chunks?doc_id=xxx&page_size=20`

### 5.3 状态栏

`StatusBar.vue` 挂载时调 `GET /api/status`,渲染 4 个可点 chip。

## 6. 错误处理

### 6.1 后端

- pipeline 未初始化 → `503` + `{"detail": "..."}`
- 参数校验失败 → FastAPI 默认 `422`
- 资源找不到(`/api/chunks/{id}`)→ `404`
- 列表为空 → `200` + `{"items": [], "total": 0, ...}`

### 6.2 前端

- `api()` 包装函数:HTTP 非 2xx 抛 `Error`(`r.status` / `r.statusText` 写入 message)
- 全局错误:顶部红色 banner "服务暂不可用,请稍后重试",5 秒自动消失
- 单卡片"查看完整切片"失败:错误信息显示在 Modal 内,不打断全局
- 空状态:列表为空显示插画 + "未找到匹配结果,试试调整筛选条件"
- 路由 404:NotFoundView 提示回到搜索

### 6.3 日志

- 前端 `console.error` 仅在 `import.meta.env.DEV` 下输出
- 后端继续用现有 logging,新端点不引入新 logger

## 7. 测试策略

### 7.1 后端(沿用 TDD)

扩展 `tests/unit/test_api.py`:

```python
test_documents_endpoint_with_filters
test_documents_endpoint_pagination
test_documents_endpoint_sorting
test_chunks_endpoint_by_doc_id
test_chunks_endpoint_by_chunk_type
test_chunks_detail_404
test_chunks_detail_returns_full_text
test_watch_dirs_endpoint
test_jobs_endpoint_filters_by_status
test_api_prefix_applied_to_all_endpoints
test_spa_fallback_serves_index_html
test_documents_sort_whitelist_rejects_unknown_field
```

测试用 `tmp_path` + 临时 SQLite,继续 mock retrieval。

### 7.2 前端

Vitest + `@vue/test-utils`,只覆盖关键组件:

- `Pagination.test.ts` - 分页边界(prev/next 禁用、跳页)
- `StatusBadge.test.ts` - score 区间映射颜色
- `ScoreBadge.test.ts` - score 区间到 CSS class
- `SearchView.test.ts` - 渲染 mock 数据 / 空状态 / 加载状态
- `api.test.ts` - 错误处理 / 超时

不做 E2E(Playwright),YAGNI。

### 7.3 手动验证清单

- `uv run python -m kb_api` + `cd frontend && npm run dev` 联调
- 4 个页面跑一遍空数据 / 有数据场景
- 验证深色主题颜色一致性
- 验证状态栏点击跳转、卡片"查看完整切片"弹窗、行内展开

## 8. 实施顺序(预告)

具体步骤由后续 writing-plans 生成,大致顺序:

1. 后端:给所有端点加 `/api` 前缀 + 新增 5 个列表/详情端点 + 写测试
2. 前端:初始化 Vite + Vue 项目,实现 SearchView(替换现有静态页)
3. 前端:实现 DocumentsView + ChunksView(行内展开 + Modal)
4. 前端:实现 WatchDirsView + JobsView + 状态栏可点跳转
5. 联调 + 手动验证 + 清理 `kb_api/static/index.html`

## 9. 不做的事(YAGNI)

- 不引入 Pinia / Vuex(列表数据局部就够)
- 不做 E2E 测试(单机工具)
- 不做 i18n(只中文)
- 不做认证(单机内网)
- 不在列表页加任何操作按钮(用户明确要求)
- 不动 MCP server / CLI(零影响)

## 10. 风险与缓解

| 风险 | 缓解 |
|------|------|
| `/api` 前缀破坏老前端引用 | 一次性切换到 Vue 前端,旧 `kb_api/static/index.html` 在最后一步删除 |
| `tree-sitter` 老版本导致 chunk 解析慢 | 列表端点用 `text_truncated`,不返回全文 |
| Vite dev server 在 Windows 上路径解析问题 | 用绝对路径 `/api/`,proxy 用 target + changeOrigin |
| 生产部署忘记 build frontend | `kb_api/__main__.py` 启动时检测 `frontend/dist`,缺失则警告 |
