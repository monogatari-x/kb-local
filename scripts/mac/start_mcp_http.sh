#!/bin/sh
# kb-local MCP HTTP server 启动脚本(macOS,launchd 调用;对应 Windows 版 start_mcp_http.bat)
# 日志: ~/.kb/mcp_http.log;端口 8765,仅监听 127.0.0.1
# 注意:本脚本在 macOS 上尚未实测,首台 mac 部署时请验证。
# 鉴权:跨机暴露时 export KB_MCP_TOKEN=<token> 并设 KB_MCP_HOST=0.0.0.0

KB_PROJECT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
LOG_DIR="$HOME/.kb"
mkdir -p "$LOG_DIR"

export KB_MCP_TRANSPORT=http
export KB_MCP_PORT=8765
export HF_HUB_OFFLINE=1
export PYTHONUNBUFFERED=1

unset ALL_PROXY all_proxy HTTP_PROXY http_proxy HTTPS_PROXY https_proxy 2>/dev/null

echo "[$(date '+%Y/%m/%d %H:%M:%S')] starting kb_mcp (dir=$KB_PROJECT_DIR)" >> "$LOG_DIR/mcp_http.log"

wait_qdrant() {
    waited=0
    while [ $waited -lt 180 ]; do
        if curl -s -o /dev/null http://127.0.0.1:6333; then
            echo "[$(date '+%Y/%m/%d %H:%M:%S')] Qdrant is ready (waited ${waited}s)" >> "$LOG_DIR/mcp_http.log"
            return 0
        fi
        waited=$((waited + 5))
        sleep 5
    done
    echo "[$(date '+%Y/%m/%d %H:%M:%S')] Qdrant not ready within 180s, starting anyway" >> "$LOG_DIR/mcp_http.log"
}

while true; do
    wait_qdrant
    "$KB_PROJECT_DIR/.venv/bin/python" -m kb_mcp >> "$LOG_DIR/mcp_http.log" 2>&1
    code=$?
    echo "[$(date '+%Y/%m/%d %H:%M:%S')] kb_mcp exited with code $code, restarting in 5s" >> "$LOG_DIR/mcp_http.log"
    sleep 5
done
