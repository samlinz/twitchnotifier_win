#Requires -RunAsAdministrator

$Pwd = (Get-Location).Path
$Name = 'TwitchNotifier'
$ExistingTask = Get-ScheduledTask -TaskName $name -ErrorAction Ignore

$FullPythonPath = (Resolve-Path $(Join-Path $Pwd '.\Scripts\pythonw.exe')).Path

# Remove task if it exists.

if ($ExistingTask -ne $null) {
    Write-Host 'Task exists already, removing...'
    Unregister-ScheduledTask -TaskName $Name
    Write-Host "Task $Name removed"
    exit
}

# Task does not exists, create new.

Write-Host "Task $Name does not exist, creating new scheduled task"

$Action = New-ScheduledTaskAction -Execute $FullPythonPath -Argument '.\twitchnotify_win.py' -WorkingDirectory $Pwd
$Trigger = New-ScheduledTaskTrigger -AtLogOn

Register-ScheduledTask -Action $Action -TaskName $Name -Description 'Background Python script that polls Twitch API to check who is online and shows Toast notification when someone goes online' -Trigger $Trigger

Write-Host "Task $Name create"

Write-Host -NoNewLine 'Press any key to continue...';
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown');