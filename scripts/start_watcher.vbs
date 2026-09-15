' 静默启动 kb-local watcher(无 cmd 窗口闪现)
' 由任务计划程序在用户登录时调用

Set fso = CreateObject("Scripting.FileSystemObject")
Set objShell = CreateObject("WScript.Shell")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
objShell.Run "cmd /c """ & scriptDir & "\start_watcher.bat""", 0, False
