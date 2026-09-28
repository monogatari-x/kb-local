# Generate the "search access invite card": a text block you can forward to colleagues.
# Admin runs this from the kb-local repo root:
#   powershell -ExecutionPolicy Bypass -File scripts\make_invite.ps1
# Output: kb-invite.txt on Desktop. (This file needs UTF-8 BOM for PS5.1 - kept via content below.)

$ErrorActionPreference = "Stop"
$kbHome = Join-Path $env:USERPROFILE ".kb"
$tokenFile = Join-Path $kbHome "central_token.local"
if (-not (Test-Path $tokenFile)) {
    Write-Host "Local token copy not found ($tokenFile). Fetch from server:"
    Write-Host '  ssh caopingtao@192.168.0.10 "grep KB_MCP_TOKEN ~/.kb/central.env"'
    exit 1
}
$token = (Get-Content $tokenFile -Raw).Trim()

$lines = @(
    '========= kb-local 知识库搜索接入卡 =========',
    '',
    '用法:给你的 AI 助手加一条配置,即可搜索全公司知识库(260+ 篇项目文档)。',
    '',
    '[Claude Code] 在命令行执行:',
    ("claude mcp add --transport http kb-local http://192.168.0.10:8766/mcp --header `"Authorization: Bearer " + $token + "`" -s user"),
    '',
    '[Codex] 在命令行执行(先设置环境变量,再开 Codex):',
    ('setx KB_MCP_TOKEN "' + $token + '"'),
    'codex mcp add kb-local --url http://192.168.0.10:8766/mcp',
    '',
    '然后重启 AI 工具,试着问一句"用 kb_search 搜一下 xxx"即可。',
    '',
    '注意:',
    '- 需在公司内网使用;token 请勿外传',
    '- 想让自己项目的文档也被收录:文档写在 <项目>/docs/ 目录下,',
    '  并找管理员配置"自动归档"(setup_contributor.ps1,10 分钟)',
    '=============================================='
)
$out = Join-Path ([Environment]::GetFolderPath("Desktop")) "kb-invite.txt"
$lines | Set-Content -Encoding utf8 -Path $out
Write-Host "已生成: $out (直接把文件内容发给同事)"
