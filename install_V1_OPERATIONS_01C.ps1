$ErrorActionPreference = "Stop"

$ProjectRoot = "D:\Projects\Hisse-Robotu"
$Files = @(
    "backend\dashboard.py",
    "backend\tests\test_v1_operations_01c_dashboard_wiring.py"
)

foreach ($Relative in $Files) {
    $Source = Join-Path $PSScriptRoot $Relative
    $Target = Join-Path $ProjectRoot $Relative

    if (-not (Test-Path $Source)) {
        throw "SOURCE_NOT_FOUND: $Source"
    }

    $TargetDir = Split-Path $Target -Parent
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null

    if (Test-Path $Target) {
        $SafeName = ($Relative -replace '[\\/:*?"<>|]', '_')
        $BackupDir = Join-Path $ProjectRoot "_backup\V1-OPERATIONS-01C"
        New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
        Copy-Item $Target (Join-Path $BackupDir $SafeName) -Force
    }

    Copy-Item $Source $Target -Force
    Write-Host "APPLIED=$Target"
}

Set-Location $ProjectRoot

python -m py_compile backend/dashboard.py
if ($LASTEXITCODE -ne 0) { throw "DASHBOARD_PY_COMPILE_FAILED" }

python -m pytest backend/tests/test_v1_operations_01c_dashboard_wiring.py -v
if ($LASTEXITCODE -ne 0) { throw "TARGET_TEST_FAILED" }
