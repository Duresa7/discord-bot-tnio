# Register a Windows Task Scheduler task that runs bot.py every 5 minutes,
# and 1 minute after each Windows sign-in. It stays on after a restart.
# Run once, in PowerShell, from any folder:  .\scripts\install_task.ps1
# Remove the task:  Unregister-ScheduledTask -TaskName "Discord Calendar Bot"

$ErrorActionPreference = "Stop"
$taskName = "Discord Calendar Bot"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\pythonw.exe"  # pythonw = no console window
if (-not (Test-Path $python)) { throw "Not found: $python. Make the .venv first (see README)." }

$action = New-ScheduledTaskAction -Execute $python -Argument "`"$root\bot.py`"" -WorkingDirectory $root
$repeat = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5)
$logon = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$logon.Delay = "PT1M"  # wait 1 minute after sign-in, so the internet connection is ready
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 4)

try {
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger @($repeat, $logon) `
        -Settings $settings -Force | Out-Null
    Write-Host "Task registered: every 5 minutes and at sign-in. Log file: $root\bot.log"
}
catch {
    # Some PCs do not allow a sign-in trigger without administrator rights.
    # The 5-minute trigger alone also continues after a restart.
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $repeat `
        -Settings $settings -Force | Out-Null
    Write-Host "Task registered: every 5 minutes (sign-in trigger not allowed here). Log file: $root\bot.log"
}
