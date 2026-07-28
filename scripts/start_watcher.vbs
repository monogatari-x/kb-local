' 静默启动 kb-local watcher(无 cmd 窗口闪现)
' 由任务计划程序在用户登录时调用

Set objShell = CreateObject("WScript.Shell")
objShell.Run "cmd /c ""C:\Glow\Projects\kb-local\scripts\start_watcher.bat""", 0, False
