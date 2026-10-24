$ErrorActionPreference = "Stop"

$Root = "D:\Projects\Hisse-Robotu"
$Patch = Join-Path $PSScriptRoot "HISSE-ROBOTU-FUND-PRESSURE-PRODUCTION-READ-MODEL-V1.patch"

if (-not (Test-Path -LiteralPath $Root)) {
    throw "REPO_NOT_FOUND=$Root"
}
if (-not (Test-Path -LiteralPath $Patch)) {
    throw "PATCH_NOT_FOUND=$Patch"
}

Set-Location $Root
$env:PYTHONPATH = "$Root\backend"

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    throw "PYTHON_NOT_FOUND=$Python"
}

Write-Host "STEP=GIT_APPLY_CHECK"
git apply --check --whitespace=nowarn $Patch
if ($LASTEXITCODE -ne 0) {
    throw "GIT_APPLY_CHECK_FAILED"
}

Write-Host "STEP=APPLY_PATCH"
git apply --whitespace=nowarn $Patch
if ($LASTEXITCODE -ne 0) {
    throw "PATCH_APPLY_FAILED"
}

$Applied = $true

try {
    Write-Host "STEP=TARGET_TESTS"
    & $Python -m pytest -q `
        backend\tests\test_fund_pressure_risk_v1.py `
        backend\tests\test_fund_pressure_read_model_v1.py `
        backend\tests\test_fund_analysis_center_ui_v1.py

    if ($LASTEXITCODE -ne 0) {
        throw "TARGET_TESTS_FAILED"
    }

    Write-Host "STEP=FULL_REGRESSION"
    & $Python -m pytest -q backend\tests

    if ($LASTEXITCODE -ne 0) {
        throw "FULL_REGRESSION_FAILED"
    }

    Write-Host ""
    Write-Host "==============================================="
    Write-Host "FUND_PRESSURE_PRODUCTION_READ_MODEL_V1=APPLIED"
    Write-Host "LATEST_FUND_SNAPSHOTS_AGGREGATION=READY"
    Write-Host "FUND_CONCENTRATION_HHI=READY"
    Write-Host "ADV20_VALUE=READY"
    Write-Host "MEDIAN_DAILY_VALUE_20=READY"
    Write-Host "LIQUIDATION_10PCT_20PCT_STRESS=READY"
    Write-Host "DOWN_VOLUME_RATIO_20D=READY"
    Write-Host "RETURN_20D=READY"
    Write-Host "DISTRIBUTION_BREADTH=READY"
    Write-Host "PRESSURE_SUBSCORES=READY"
    Write-Host "FDO_CANONICAL_SOURCE=NOT_FOUND_IN_REPO"
    Write-Host "FDO_GUESSING=NO"
    Write-Host "FDO_DISPLAY=UNAVAILABLE_UNTIL_CANONICAL_SOURCE"
    Write-Host "MARKET_REFRESH=EXPLICIT_BUTTON_ONLY"
    Write-Host "INITIAL_PAGE_NETWORK_CALL=NO"
    Write-Host "AL_SAT_MUTATION=NO"
    Write-Host "CANONICAL_RANKING_MUTATION=NO"
    Write-Host "TARGET_TESTS=PASS"
    Write-Host "FULL_REGRESSION=PASS"
    Write-Host "NEXT=FDO_CANONICAL_SOURCE_INTEGRATION"
    Write-Host "==============================================="
}
catch {
    if ($Applied) {
        Write-Host "ROLLBACK=START"
        git apply -R --whitespace=nowarn $Patch
        if ($LASTEXITCODE -eq 0) {
            Write-Host "ROLLBACK=PASS"
        } else {
            Write-Host "ROLLBACK=FAILED"
        }
    }
    throw
}
