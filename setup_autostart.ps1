param([switch]$Remove, [switch]$Kiosk)
$ErrorActionPreference = 'Stop'
$shortcutName = 'Anti-Trigger Fingers PC.lnk'
$startupLink = Join-Path ([Environment]::GetFolderPath('Startup')) $shortcutName
$desktopLink = Join-Path ([Environment]::GetFolderPath('Desktop')) $shortcutName
if ($Remove) {
    foreach ($link in @($startupLink, $desktopLink)) {
        if (Test-Path -LiteralPath $link) { Remove-Item -LiteralPath $link }
    }
    Write-Host 'Removed the PC app shortcuts. Program and data files were kept.'
    exit
}
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    $pythonPath = Join-Path $PSScriptRoot '..\.venv-pc-v28\Scripts\pythonw.exe'
}
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Run install_pc.bat first.' }
$pythonPath = (Resolve-Path -LiteralPath $pythonPath).Path
$launcher = Join-Path $PSScriptRoot 'launch_pc.py'
$shell = New-Object -ComObject WScript.Shell
foreach ($link in @($startupLink, $desktopLink)) {
    $shortcut = $shell.CreateShortcut($link)
    $shortcut.TargetPath = $pythonPath
    $shortcut.Arguments = '"' + $launcher + '"'
    if ($Kiosk) { $shortcut.Arguments += ' --kiosk' }
    $shortcut.WorkingDirectory = $PSScriptRoot
    $shortcut.Description = 'Anti-Trigger Fingers PC v28'
    $shortcut.Save()
}
Write-Host 'Created desktop and sign-in startup shortcuts for Anti-Trigger Fingers PC.'
