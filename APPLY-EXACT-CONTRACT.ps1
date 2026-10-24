$ErrorActionPreference = "Stop"

$ProjectRoot = "D:\Projects\Hisse-Robotu"
$Source = Join-Path $PSScriptRoot "backend\app\workflow\production_intelligence_final_lock.py"
$Target = Join-Path $ProjectRoot "backend\app\workflow\production_intelligence_final_lock.py"

if (-not (Test-Path $Source)) { throw "SOURCE_NOT_FOUND: $Source" }
if (-not (Test-Path $Target)) { throw "TARGET_NOT_FOUND: $Target" }

$Backup = "$Target.bak-exact-contract"
Copy-Item $Target $Backup -Force
Copy-Item $Source $Target -Force

Write-Host "OVERWRITE_OK=$Target"
Write-Host "BACKUP=$Backup"

python -m pytest "$ProjectRoot\backend\tests\test_ev14_final_production_lock.py" -v --cache-clear
