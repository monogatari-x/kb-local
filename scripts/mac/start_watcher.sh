#!/bin/sh
# kb-local watcher 启动脚本(macOS;对应 Windows 版 start_watcher.bat)
# 注意:本脚本在 macOS 上尚未实测,首台 mac 部署时请验证。

KB_PROJECT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
LOG_DIR="$HOME/.kb"
mkdir -p "$LOG_DIR"

export HF_HUB_OFFLINE=1
export PYTHONUNBUFFERED=1

unset ALL_PROXY all_proxy HTTP_PROXY http_proxy HTTPS_PROXY https_proxy 2>/dev/null

cd "$KB_PROJECT_DIR" || exit 1
[ -f "$LOG_DIR/watcher.log" ] && mv "$LOG_DIR/watcher.log" "$LOG_DIR/watcher.prev.log"

echo "[$(date '+%Y/%m/%d %H:%M:%S')] starting kb watch (dir=$KB_PROJECT_DIR)" >> "$LOG_DIR/watcher.log"
uv run kb watch start >> "$LOG_DIR/watcher.log" 2>&1
echo "[$(date '+%Y/%m/%d %H:%M:%S')] watcher exited with code $?" >> "$LOG_DIR/watcher.log"
