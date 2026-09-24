# Register a Windows Task Scheduler task that runs bot.py every 5 minutes.
# Run once, in PowerShell, from any folder:  .\scripts\install_task.ps1
# Remove the task:  Unregister-ScheduledTask -TaskName "Discord Calendar Bot"

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\pythonw.exe"  # pythonw = no console window
if (-not (Test-Path $python)) { throw "Not found: $python. Make the .venv first (see README)." }

$action = New-ScheduledTaskAction -Execute $python -Argument "`"$root\bot.py`"" -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5)
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 4)

Register-ScheduledTask -TaskName "Discord Calendar Bot" -Action $action -Trigger $trigger -Settings $settings -Force
Write-Host "Task registered. Log file: $root\bot.log"
