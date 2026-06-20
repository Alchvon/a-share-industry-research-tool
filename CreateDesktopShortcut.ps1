$ErrorActionPreference = "Stop"
$shortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "A股产业链龙头分析器.lnk"
$target = Join-Path $PSScriptRoot "启动分析器.cmd"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $target
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.Description = "打开 A股产业链龙头分析器"
$shortcut.IconLocation = "$env:SystemRoot\System32\imageres.dll,109"
$shortcut.Save()
Write-Host "Desktop shortcut created: $shortcutPath"
Start-Sleep -Seconds 2
