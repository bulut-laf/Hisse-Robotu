$ErrorActionPreference = "Stop"

$Root = "D:\Projects\Hisse-Robotu"
$Patch = Join-Path $PSScriptRoot "HISSE-ROBOTU-FUND-ANALYSIS-NON-BLOCKING-ENTRY-V1.patch"

if (-not (Test-Path -LiteralPath $Root)) {
    throw "REPO_NOT_FOUND=$Root"
}
if (-not (Test-Path -LiteralPath $Patch)) {
    throw "PATCH_NOT_FOUND=$Patch"
}

$Python = if (Test-Path (Join-Path $Root ".venv\Scripts\python.exe")) {
    Join-Path $Root ".venv\Scripts\python.exe"
} else {
    "python"
}

Set-Location $Root

Write-Host "STEP=GIT_APPLY_CHECK"
& git apply --check $Patch
if ($LASTEXITCODE -ne 0) {
    throw "GIT_APPLY_CHECK_FAILED"
}
Write-Host "GIT_APPLY_CHECK=PASS"

Write-Host "STEP=GIT_APPLY"
& git apply $Patch
if ($LASTEXITCODE -ne 0) {
    throw "GIT_APPLY_FAILED"
}
Write-Host "GIT_APPLY=PASS"

$OldPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = "$Root\backend"

    Write-Host "STEP=TARGET_TESTS"
    & $Python -m pytest -q `
        backend/tests/test_fund_analysis_non_blocking_entry_v1.py `
        backend/tests/test_fund_analysis_center_ui_v1.py `
        backend/tests/test_fund_kap_portfolio_ingestion_v1.py `
        backend/tests/test_fund_production_store_runtime_v1.py
    if ($LASTEXITCODE -ne 0) {
        throw "TARGET_TESTS_FAILED"
    }

    Write-Host "STEP=FULL_REGRESSION"
    & $Python -m pytest -q backend/tests
    if ($LASTEXITCODE -ne 0) {
        throw "FULL_REGRESSION_FAILED"
    }
}
finally {
    $env:PYTHONPATH = $OldPythonPath
}

Write-Host ""
Write-Host "==============================================="
Write-Host "FUND_ANALYSIS_NON_BLOCKING_ENTRY=APPLIED"
Write-Host "INITIAL_TEFAŞ_NETWORK_CALL=DISABLED"
Write-Host "EXPLICIT_TEFAŞ_REFRESH_BUTTON=READY"
Write-Host "LAST_GOOD_RESULTS_ON_REFRESH_FAILURE=PRESERVED"
Write-Host "KAP_PORTFOLIO_IMPORT_AVAILABLE_WITHOUT_TEFAŞ_WAIT=YES"
Write-Host "TARGET_TESTS=PASS"
Write-Host "FULL_REGRESSION=PASS"
Write-Host "AL_SAT_MUTATION=NO"
Write-Host "CANONICAL_RANKING_MUTATION=NO"
Write-Host "NEXT=LIVE_KAP_PORTFOLIO_SMOKE"
Write-Host "==============================================="
