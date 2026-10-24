param(
    [string]$Repo = "D:\Projects\Hisse-Robotu",
    [string]$Python = ""
)

$ErrorActionPreference = "Stop"

if (-not $Python) {
    $Python = Join-Path $Repo ".venv\Scripts\python.exe"
}

if (-not (Test-Path $Repo)) {
    throw "Repo bulunamadı: $Repo"
}
if (-not (Test-Path $Python)) {
    throw "Python bulunamadı: $Python"
}

$module = "backend.app.operations.daily_buy_decision_scheduled_runner"

$eveningAction = New-ScheduledTaskAction `
    -Execute $Python `
    -Argument "-m $module --phase EVENING" `
    -WorkingDirectory $Repo
$eveningTrigger = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday `
    -At 18:20

$morningAction = New-ScheduledTaskAction `
    -Execute $Python `
    -Argument "-m $module --phase MORNING" `
    -WorkingDirectory $Repo
$morningTrigger = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday `
    -At 09:00

Register-ScheduledTask `
    -TaskName "HisseRobotu-EOD-DailyDecision" `
    -Action $eveningAction `
    -Trigger $eveningTrigger `
    -Description "Hisse Robotu seans sonu ertesi gün karar listesi" `
    -Force | Out-Null

Register-ScheduledTask `
    -TaskName "HisseRobotu-0900-DailyDecision" `
    -Action $morningAction `
    -Trigger $morningTrigger `
    -Description "Hisse Robotu 09:00 sabah yeniden değerlendirme" `
    -Force | Out-Null

Write-Host "Kuruldu: HisseRobotu-EOD-DailyDecision (18:20 hafta içi)"
Write-Host "Kuruldu: HisseRobotu-0900-DailyDecision (09:00 hafta içi)"
