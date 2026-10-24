$ErrorActionPreference = "Stop"

$ProjectRoot = "D:\Projects\Hisse-Robotu"
$Source = Join-Path $PSScriptRoot "backend\app\workflow\production_intelligence_final_lock.py"
$Target = Join-Path $ProjectRoot "backend\app\workflow\production_intelligence_final_lock.py"

if (-not (Test-Path $Source)) {
    throw "SOURCE_NOT_FOUND: $Source"
}

if (-not (Test-Path (Split-Path $Target -Parent))) {
    throw "TARGET_DIR_NOT_FOUND: $(Split-Path $Target -Parent)"
}

$Backup = "$Target.bak-final-lock"
Copy-Item $Target $Backup -Force
Copy-Item $Source $Target -Force

Write-Host "OVERWRITE_OK=$Target"
Write-Host "BACKUP=$Backup"

$FirstLine = Get-Content $Target -TotalCount 1
Write-Host "FIRST_LINE=$FirstLine"

if ($FirstLine -eq "@'") {
    throw "OVERWRITE_FAILED_OLD_POWERSHELL_TEXT_STILL_PRESENT"
}

python -m pytest "$ProjectRoot\backend\tests\test_ev14_final_production_lock.py" -v --cache-clear
