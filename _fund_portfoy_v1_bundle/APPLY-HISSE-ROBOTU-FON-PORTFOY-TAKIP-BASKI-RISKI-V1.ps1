$ErrorActionPreference = "Stop"

$Root = "D:\Projects\Hisse-Robotu"
$Patch = Join-Path $PSScriptRoot "HISSE-ROBOTU-FON-PORTFOY-TAKIP-BASKI-RISKI-V1.patch"

if (-not (Test-Path $Root)) {
    throw "REPO_NOT_FOUND=$Root"
}
if (-not (Test-Path $Patch)) {
    throw "PATCH_NOT_FOUND=$Patch"
}

Push-Location $Root
try {
    Write-Host "FUND_PORTFOLIO_PRESSURE_V1"
    Write-Host "STEP=GIT_APPLY_CHECK"
    git apply --check --whitespace=error-all $Patch
    if ($LASTEXITCODE -ne 0) { throw "GIT_APPLY_CHECK_FAILED" }

    Write-Host "STEP=GIT_APPLY"
    git apply --whitespace=error-all $Patch
    if ($LASTEXITCODE -ne 0) { throw "GIT_APPLY_FAILED" }

    $Python = if (Test-Path ".venv\Scripts\python.exe") {
        ".venv\Scripts\python.exe"
    } else {
        "python"
    }

    Write-Host "STEP=TARGET_TESTS"
    & $Python -m pytest -q `
        backend/tests/test_fund_risk_metrics_v1.py `
        backend/tests/test_fund_portfolio_tracking_v1.py `
        backend/tests/test_fund_pressure_risk_v1.py
    if ($LASTEXITCODE -ne 0) { throw "TARGET_TESTS_FAILED" }

    Write-Host "STEP=FULL_REGRESSION"
    & $Python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "FULL_REGRESSION_FAILED" }

    Write-Host ""
    Write-Host "FUND_PORTFOLIO_SNAPSHOT_CHANGE_ENGINE=APPLIED"
    Write-Host "FUND_PRESSURE_RAW_METRICS=APPLIED"
    Write-Host "THREE_OBSERVATIONAL_SUBSCORES=APPLIED"
    Write-Host "AUTOMATIC_TRADE_AUTHORITY=NONE"
    Write-Host "AL_SAT_MUTATION=NO"
    Write-Host "CANONICAL_RANKING_MUTATION=NO"
    Write-Host "TARGET_TESTS=PASS"
    Write-Host "FULL_REGRESSION=PASS"
    Write-Host "NEXT=FUND_ANALYSIS_UI_BRIDGE_EXACT_SOURCE"
}
finally {
    Pop-Location
}
