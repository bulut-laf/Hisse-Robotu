param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$module = "backend.app.operations.scheduled_operation_phase_runner"
$legacyModule = "backend.app.operations.daily_buy_decision_scheduled_runner"

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "PYTHON_NOT_FOUND=$python"
}

$runnerPath = Join-Path $ProjectRoot "backend\app\operations\scheduled_operation_phase_runner.py"
if (-not (Test-Path -LiteralPath $runnerPath -PathType Leaf)) {
    throw "PHASE_RUNNER_NOT_FOUND=$runnerPath"
}

# Existing Windows Task Scheduler framework, upgraded to four operation phases.
# Legacy decision engine is preserved behind CANONICAL_CLOSE delegation.
# No parallel scheduler is created.

$weekdays = @(
    [System.DayOfWeek]::Monday,
    [System.DayOfWeek]::Tuesday,
    [System.DayOfWeek]::Wednesday,
    [System.DayOfWeek]::Thursday,
    [System.DayOfWeek]::Friday
)

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

$taskSpecs = @(
    @{
        Name = "HisseRobotu-0845-PreOpen"
        Phase = "PREOPEN"
        At = "08:45"
        Description = "Hisse Robotu 08:45 preopen context; read-only."
    },
    @{
        Name = "HisseRobotu-1020-PostOpen"
        Phase = "POSTOPEN"
        At = "10:20"
        Description = "Hisse Robotu 10:20 postopen gap and entry evidence; not an AL/SAT decision."
    },
    @{
        Name = "HisseRobotu-1720-PreClose"
        Phase = "PRECLOSE"
        At = "17:20"
        Description = "Hisse Robotu 17:20 partial-session preclose preview; not canonical."
    },
    @{
        Name = "HisseRobotu-1830-CanonicalClose"
        Phase = "CANONICAL_CLOSE"
        At = "18:30"
        Description = "Hisse Robotu 18:30 canonical close through existing legacy EVENING authority."
    }
)

$legacyTaskNames = @(
    "HisseRobotu-EOD-DailyDecision"
)

foreach ($legacyName in $legacyTaskNames) {
    $legacy = Get-ScheduledTask -TaskName $legacyName -ErrorAction SilentlyContinue
    if ($null -ne $legacy) {
        Unregister-ScheduledTask `
            -TaskName $legacyName `
            -Confirm:$false `
            -ErrorAction Stop
        Write-Host "LEGACY_TASK_REMOVED=$legacyName"
    }
}

foreach ($spec in $taskSpecs) {
    $action = New-ScheduledTaskAction `
        -Execute $python `
        -Argument "-m $module --phase $($spec.Phase)" `
        -WorkingDirectory $ProjectRoot

    $trigger = New-ScheduledTaskTrigger `
        -Weekly `
        -WeeksInterval 1 `
        -DaysOfWeek $weekdays `
        -At $spec.At

    Register-ScheduledTask `
        -TaskName $spec.Name `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Description $spec.Description `
        -Force | Out-Null

    Write-Host "TASK_REGISTERED=$($spec.Name)|PHASE=$($spec.Phase)|AT=$($spec.At)"
}


# Compatibility preservation:
# POSTOPEN is evidence-only and must not replace the existing MORNING decision run.
# Keep the legacy MORNING decision task until a separately proven bridge exists.
$morningAction = New-ScheduledTaskAction `
    -Execute $python `
    -Argument "-m $legacyModule --phase MORNING" `
    -WorkingDirectory $ProjectRoot

$morningTrigger = New-ScheduledTaskTrigger `
    -Weekly `
    -WeeksInterval 1 `
    -DaysOfWeek $weekdays `
    -At "09:00"

Register-ScheduledTask `
    -TaskName "HisseRobotu-0900-DailyDecision" `
    -Action $morningAction `
    -Trigger $morningTrigger `
    -Settings $settings `
    -Description "Hisse Robotu legacy MORNING decision compatibility run; preserved until a proven replacement exists." `
    -Force | Out-Null

Write-Host "COMPATIBILITY_TASK_REGISTERED=HisseRobotu-0900-DailyDecision|PHASE=MORNING|AT=09:00"

Write-Host "FOUR_PHASE_WINDOWS_TASK_INSTALL=SUCCESS"
Write-Host "PARALLEL_SCHEDULER=NO"
Write-Host "LEGACY_18_20_TASK=RETIRED"
Write-Host "LEGACY_09_00_MORNING_DECISION=PRESERVED"
