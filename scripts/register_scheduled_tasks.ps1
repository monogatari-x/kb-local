# 注册 kb-local MCP HTTP 服务为 Windows 计划任务(需管理员权限运行一次)
# 由 UAC 提权的 PowerShell 执行;结果写入 ~/.kb/register_task.log

$ErrorActionPreference = "Stop"
$log = "$env:USERPROFILE\.kb\register_task.log"
"[$(Get-Date)] registering kb-local-mcp-http..." | Out-File $log -Encoding utf8

try {
    $act = New-ScheduledTaskAction -Execute "wscript.exe" `
        -Argument '"D:\Glow\Projects\kb-local\scripts\start_mcp_http.vbs"'
    $trg = New-ScheduledTaskTrigger -AtLogOn
    $set = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit ([TimeSpan]::Zero) `
        -MultipleInstances IgnoreNew `
        -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1)
    Register-ScheduledTask -TaskName "kb-local-mcp-http" -Action $act -Trigger $trg `
        -Settings $set -Force `
        -Description "kb-local MCP server (HTTP, port 8765) - shared by Claude Code/Codex sessions" | Out-Null
    "[$(Get-Date)] OK: kb-local-mcp-http registered (AtLogOn, KeepAlive/Restart)" | Out-File $log -Append -Encoding utf8
    exit 0
}
catch {
    "[$(Get-Date)] FAILED: $($_.Exception.Message)" | Out-File $log -Append -Encoding utf8
    exit 1
}
