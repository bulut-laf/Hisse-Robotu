$ErrorActionPreference = "Stop"

$Root = "D:\Projects\Hisse-Robotu"
$Patch = Join-Path $PSScriptRoot "HISSE-ROBOTU-FUND-PROFILE-LIVE-UX-COMPLETION-V1.patch"

if (-not (Test-Path -LiteralPath $Root)) { throw "REPO_NOT_FOUND=$Root" }
if (-not (Test-Path -LiteralPath $Patch)) { throw "PATCH_NOT_FOUND=$Patch" }

Set-Location $Root
$env:PYTHONPATH = "$Root\backend"
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) { throw "PYTHON_NOT_FOUND=$Python" }

Write-Host "STEP=GIT_APPLY_CHECK"
git apply --check --whitespace=nowarn $Patch
if ($LASTEXITCODE -ne 0) { throw "GIT_APPLY_CHECK_FAILED" }

Write-Host "STEP=APPLY_PATCH"
git apply --whitespace=nowarn $Patch
if ($LASTEXITCODE -ne 0) { throw "PATCH_APPLY_FAILED" }

$Applied = $true

try {
    Write-Host "STEP=TARGET_TESTS"
    & $Python -m pytest -q `
        backend\tests\test_fund_profile_auto_refresh_v1.py `
        backend\tests\test_fund_analysis_center_ui_v1.py `
        backend\tests\test_fund_f4_money_flow_v1.py `
        backend\tests\test_fund_tefas_history_population_v1.py `
        backend\tests\test_fund_pressure_read_model_v1.py `
        backend\tests\test_fund_kap_portfolio_auto_ingestion_v1.py `
        backend\tests\test_fund_kap_free_float_auto_population_v1.py

    if ($LASTEXITCODE -ne 0) { throw "TARGET_TESTS_FAILED" }

    Write-Host "STEP=FULL_REGRESSION"
    & $Python -m pytest -q backend\tests
    if ($LASTEXITCODE -ne 0) { throw "FULL_REGRESSION_FAILED" }

    Write-Host ""
    Write-Host "======================================================"
    Write-Host "FUND_PROFILE_LIVE_UX_COMPLETION_V1=APPLIED"
    Write-Host "PRICE_HISTORY_CHART=READY"
    Write-Host "FUND_SIZE_HISTORY_CHART=READY"
    Write-Host "INVESTOR_HISTORY_CHART=READY"
    Write-Host "LATEST_PORTFOLIO_CHANGE_SUMMARY=READY"
    Write-Host "NEW_ENTRY_INCREASE_REDUCE_EXIT_COUNTS=READY"
    Write-Host "DATA_FRESHNESS_PANEL=READY"
    Write-Host "ONE_PAGE_FUND_PROFILE=ENHANCED"
    Write-Host "AUTO_REFRESH_CONTRACT=PRESERVED"
    Write-Host "MANUAL_TOOLS=FALLBACK"
    Write-Host "AL_SAT_MUTATION=NO"
    Write-Host "CANONICAL_RANKING_MUTATION=NO"
    Write-Host "TARGET_TESTS=PASS"
    Write-Host "FULL_REGRESSION=PASS"
    Write-Host "NEXT=FUND_PROFILE_VISIBLE_LIVE_QA"
    Write-Host "======================================================"
}
catch {
    if ($Applied) {
        Write-Host "ROLLBACK=START"
        git apply -R --whitespace=nowarn $Patch
        if ($LASTEXITCODE -eq 0) { Write-Host "ROLLBACK=PASS" }
        else { Write-Host "ROLLBACK=FAILED" }
    }
    throw
}
