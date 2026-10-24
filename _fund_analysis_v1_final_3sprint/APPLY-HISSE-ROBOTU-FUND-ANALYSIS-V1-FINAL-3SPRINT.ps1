$ErrorActionPreference = "Stop"

$Root = "D:\Projects\Hisse-Robotu"
$Patch = Join-Path $PSScriptRoot "HISSE-ROBOTU-FUND-ANALYSIS-V1-FINAL-3SPRINT.patch"

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
        backend\tests\test_fund_kap_free_float_auto_population_v1.py `
        backend\tests\test_fund_free_float_canonical_source_v1.py `
        backend\tests\test_fund_pressure_read_model_v1.py `
        backend\tests\test_fund_pressure_risk_v1.py `
        backend\tests\test_fund_kap_portfolio_auto_ingestion_v1.py `
        backend\tests\test_fund_kap_portfolio_ingestion_v1.py `
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
    Write-Host "======================================================"
    Write-Host "FUND_ANALYSIS_V1_FINAL_3SPRINT=APPLIED"
    Write-Host "SPRINT_1_FDO_OFFICIAL_KAP_AUTO_POPULATION=READY"
    Write-Host "KAP_BIST_COMPANY_DIRECTORY_DISCOVERY=READY"
    Write-Host "KAP_COMPANY_GENERAL_PAGE_RESOLUTION=READY"
    Write-Host "KAP_FREE_FLOAT_PARSE=READY"
    Write-Host "FDO_CANONICAL_STORE_AUTO_WRITE=READY"
    Write-Host "FDO_SOURCE=KAP_ONLY"
    Write-Host "FDO_OBSERVATION_DATE=REQUIRED"
    Write-Host "FDO_DUPLICATE_GUARD=YES"
    Write-Host "FDO_FAILURE_ISOLATION=YES"
    Write-Host "SPRINT_2_FUND_PRESSURE_FULL_PRODUCTION=READY"
    Write-Host "FUND_FDO_RATIO=LIVE_WHEN_KAP_FDO_AVAILABLE"
    Write-Host "ADV20_LIQUIDITY=LIVE"
    Write-Host "CONCENTRATION_HHI=LIVE"
    Write-Host "DISTRIBUTION_BREADTH=LIVE"
    Write-Host "PRESSURE_SUBSCORES=LIVE"
    Write-Host "FULL_PRODUCTION_REFRESH_BUTTON=READY"
    Write-Host "SPRINT_3_PRODUCTION_HARDENING=READY"
    Write-Host "NETWORK_CALL_ON_PAGE_OPEN=NO"
    Write-Host "EXPLICIT_REFRESH_ONLY=YES"
    Write-Host "NON_KAP_FDO_GUESSING=NO"
    Write-Host "UNRESOLVED_SYMBOLS=FAIL_CLOSED"
    Write-Host "PER_SYMBOL_FAILURE_ISOLATION=YES"
    Write-Host "MANUAL_FDO_IMPORT=FALLBACK"
    Write-Host "MANUAL_PORTFOLIO_PDF=FALLBACK"
    Write-Host "AL_SAT_MUTATION=NO"
    Write-Host "CANONICAL_RANKING_MUTATION=NO"
    Write-Host "TARGET_TESTS=PASS"
    Write-Host "FULL_REGRESSION=PASS"
    Write-Host "NEXT=FINAL_LIVE_SMOKE"
    Write-Host "======================================================"
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
