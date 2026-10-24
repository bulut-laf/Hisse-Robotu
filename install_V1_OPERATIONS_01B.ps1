$ErrorActionPreference = "Stop"

$ProjectRoot = "D:\Projects\Hisse-Robotu"
$Files = @(
    "backend\app\analysis\morning_operation_snapshot.py",
    "backend\tests\test_morning_operation_snapshot.py"
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
        Copy-Item $Target "$Target.bak-v1-operations-01b" -Force
    }

    Copy-Item $Source $Target -Force
    Write-Host "APPLIED=$Target"
}

Set-Location $ProjectRoot
python -m pytest backend/tests/test_morning_operation_snapshot.py -v
