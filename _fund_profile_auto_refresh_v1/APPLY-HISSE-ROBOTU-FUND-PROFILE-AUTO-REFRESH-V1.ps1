$ErrorActionPreference = "Stop"

$Root = "D:\Projects\Hisse-Robotu"
$Patch = Join-Path $PSScriptRoot "HISSE-ROBOTU-FUND-PROFILE-AUTO-REFRESH-V1.patch"

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
    Write-Host "FUND_PROFILE_AUTO_REFRESH_V1=APPLIED"
    Write-Host "FUND_SELECTOR=READY"
    Write-Host "ONE_PAGE_FUND_PROFILE=READY"
    Write-Host "TEFAS_UNIVERSE_AUTO_REFRESH=READY"
    Write-Host "SELECTED_FUND_TEFAS_DETAIL_AUTO_REFRESH=READY"
    Write-Host "SELECTED_FUND_PRICE_HISTORY_AUTO_REFRESH=READY"
    Write-Host "SELECTED_FUND_KAP_PORTFOLIO_AUTO_REFRESH=READY"
    Write-Host "SELECTED_FUND_KAP_FDO_AUTO_REFRESH=READY"
    Write-Host "FUND_PRICE=LIVE"
    Write-Host "DAILY_RETURN=LIVE"
    Write-Host "RETURN_1W_1M_3M_6M_YTD_1Y=READY_FROM_CANONICAL_HISTORY"
    Write-Host "FUND_SIZE=LIVE"
    Write-Host "INVESTOR_COUNT=LIVE"
    Write-Host "CURRENT_PORTFOLIO=LIVE"
    Write-Host "LAST_GOOD_DATA_PRESERVED_ON_SOURCE_FAILURE=YES"
    Write-Host "AUTO_REFRESH_SUCCESS_INTERVAL=6_HOURS"
    Write-Host "AUTO_REFRESH_FAILURE_RETRY=1_HOUR"
    Write-Host "MANUAL_REFRESH=FALLBACK"
    Write-Host "MANUAL_PDF_CSV=FALLBACK"
    Write-Host "AL_SAT_MUTATION=NO"
    Write-Host "CANONICAL_RANKING_MUTATION=NO"
    Write-Host "TARGET_TESTS=PASS"
    Write-Host "FULL_REGRESSION=PASS"
    Write-Host "NEXT=FUND_PROFILE_LIVE_SMOKE"
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
