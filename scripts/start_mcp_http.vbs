' 静默启动 kb-local MCP HTTP server(无 cmd 窗口闪现)
' 由任务计划程序在用户登录时调用

Set fso = CreateObject("Scripting.FileSystemObject")
Set objShell = CreateObject("WScript.Shell")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
objShell.Run "cmd /c """ & scriptDir & "\start_mcp_http.bat""", 0, False
