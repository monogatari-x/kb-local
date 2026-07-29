# MCP kb_search 卡死问题修复(2026-07-29)

## 症状

Claude Code 调用 `kb_search` MCP 工具时,主进程卡住,日志只显示:

```
● Calling kb-local… (ctrl+o to expand)
  ⎿  "<query>"
  /btw 主进程卡住了吗?
  是的,主进程调用 kb_search 检索时遇到了内部错误(internal error),没有返回结果。
```

表现:
- `kb_status` 工具调用正常(秒级返回)
- `kb_search` 调用 60 秒后超时,返回 "internal error"
- 间歇性出现(有时能成功)
- 主进程在 Claude Code 端一直等着,无法继续

## 根因(深度排查)

排查过程层层递进,每一步都被证伪,直到找到真正的根因。

### 第一层猜想:异常未捕获?

最初怀疑 `kb_search` 工具函数没有 try/except,任何异常抛到 MCP 框架层导致主进程卡死。

**验证**:加上 try/except 重启 Claude Code,问题依然存在。

**证伪**:异常从未到达 except 块——请求根本没执行到 try 内部就卡住了。

### 第二层猜想:asyncio 事件循环阻塞?

`retrieval.search()` 是同步阻塞调用(BGE-M3 推理 + Qdrant HTTP + SQLite)。FastMCP 基于 asyncio,同步阻塞会卡住事件循环,导致 MCP server 无法把响应写回 stdout。

**验证**:把 `kb_search` 改成 async,用 `asyncio.to_thread` 把同步调用放到线程池。

**证伪**:仍然卡死。原因——FastMCP 用 `anyio.run()` 而非 `asyncio.run()` 启动事件循环,asyncio.to_thread 在 anyio 上下文里不兼容。

### 第三层猜想:anyio.to_thread.run_sync?

改用 `anyio.to_thread.run_sync` 配合 FastMCP 的事件循环。

**验证**:通过 JSON-RPC 直接调用测试——仍然 90 秒超时。

**关键日志**:
```
[kb-local] _do_search: getting retrieval  ← 线程进入了
(之后无任何输出,BGE-M3 加载从未完成)
```

**部分证伪**:线程确实启动了,但卡在 `_get_retrieval()` → BGE-M3 模型加载。

### 第四层猜想:BGE-M3 本身的问题?

直接命令行跑同样的代码:
```bash
uv run python -c "from kb_core.embeddings.bge_m3 import BGE_M3_EMBEDDER; e = BGE_M3_EMBEDDER(...)"
```

**结果**:8 秒加载,0.3 秒查询,完全正常。

子线程里加载也正常。**问题只出在 FastMCP 进程内**。

### 第五层猜想:FastMCP stdio 传输层的问题?

写一个最小 FastMCP server,工具函数 `time.sleep(10)`——通过 JSON-RPC 调用,8 秒后正常返回。

**证伪**:stdio 传输层本身没问题,能正确处理长时间阻塞的 async 工具。

### 真正的根因:PyTorch × anyio 工作线程死锁

最终验证:把 BGE-M3 模型加载放在 FastMCP 启动**之前**(主线程)执行,后续 `kb_search` 通过 anyio.to_thread 调用已加载的模型——**0.1 秒返回**。

**结论**:

PyTorch / BGE-M3 在 anyio 工作线程里首次加载会触发死锁,推测原因:
- PyTorch 初始化过程中注册 signal handler 或 OpenMP 线程池
- 在 anyio 管理的事件循环上下文里,这些操作与工作线程调度产生死锁
- 死锁发生在 GIL 层面,任何线程切换都无法进行

**关键证据**:
- 主线程加载 BGE-M3:正常,8 秒完成
- 子线程(asyncio.run 之外)加载 BGE-M3:正常,1.2 秒完成
- FastMCP 启动后的 anyio 工作线程加载 BGE-M3:**永久卡死**

## 修复方案

**核心思想**:在 `mcp.run()` 启动事件循环之前,在主线程预加载 BGE-M3 模型。后续 `kb_search` 调用直接使用已加载的模型,不再触发死锁。

### 改动文件

#### `kb_mcp/server.py`

1. **新增 `prewarm()` 函数**:在 FastMCP 启动前调用 `_build_retrieval()` 预加载模型

2. **`main()` 改为先 prewarm 再 run**:
```python
def main() -> None:
    prewarm()
    mcp.run()
```

3. **工具函数保持 async + anyio.to_thread.run_sync**:虽然模型已加载,但 Qdrant HTTP 调用仍是同步阻塞,继续用 anyio.to_thread 避免阻塞事件循环

4. **`_do_search` / `_do_status` 同步辅助函数**:实际的业务逻辑,被 anyio.to_thread 包装调用

5. **完整的 try/except 异常处理**:即使后续出现异常(Qdrant 断连等)也能返回可读的错误信息,而不是 "internal error"

### 验证

修改后的端到端测试(stdio JSON-RPC):
- 第一次 `kb_search` 调用:**0.1 秒** 返回
- 第二次 `kb_search` 调用:**0.0 秒** 返回
- 不再卡死,不再有 "internal error"

## 副作用与权衡

### 启动时间增加

- 之前:MCP server 启动 < 1 秒
- 现在:MCP server 启动多 ~8 秒(BGE-M3 加载)

但这个权衡是值得的:
- 之前:首次 kb_search 卡死或 12 秒延迟
- 现在:MCP server 启动时多等 8 秒,之后所有 kb_search 都是毫秒级

### 内存占用

BGE-M3 模型常驻内存,约 2.4GB。MCP server 进程会一直占用这部分内存。

## 教训与提示

1. **不要假设 MCP 工具卡死是简单的异常未捕获** —— 真正的根因可能是底层库(PyTorch)与 MCP 框架(anyio)的兼容问题

2. **FastMCP 用的是 anyio 不是 asyncio** —— 不能直接用 `asyncio.to_thread` 或 `asyncio.get_event_loop().run_in_executor`

3. **重 CPU/IO 操作要预加载** —— 任何在工具调用时首次加载的重型资源(PyTorch 模型、大文件、连接池),都应该在 MCP server 启动前(主线程)完成预加载

4. **排查 MCP 卡死的方法** —— 通过 JSON-RPC over stdio 直接调用,观察 stderr 日志,比在 Claude Code 里反复试更高效

## 相关文件

- `kb_mcp/server.py` — 主修复(新增 prewarm + 改 async 工具)
- `kb_mcp/__main__.py` — 已有的 HF_HUB_OFFLINE 设置(避免 HuggingFace 网络超时)
