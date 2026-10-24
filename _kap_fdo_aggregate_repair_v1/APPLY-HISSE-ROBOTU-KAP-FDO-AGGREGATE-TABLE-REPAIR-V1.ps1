$ErrorActionPreference = "Stop"

$Root = "D:\Projects\Hisse-Robotu"
$Patch = Join-Path $PSScriptRoot "HISSE-ROBOTU-KAP-FDO-AGGREGATE-TABLE-REPAIR-V1.patch"

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
        backend\tests\test_fund_kap_free_float_auto_population_v1.py `
        backend\tests\test_fund_free_float_canonical_source_v1.py `
        backend\tests\test_fund_pressure_read_model_v1.py `
        backend\tests\test_fund_pressure_risk_v1.py `
        backend\tests\test_fund_analysis_center_ui_v1.py
    if ($LASTEXITCODE -ne 0) { throw "TARGET_TESTS_FAILED" }

    Write-Host "STEP=FULL_REGRESSION"
    & $Python -m pytest -q backend\tests
    if ($LASTEXITCODE -ne 0) { throw "FULL_REGRESSION_FAILED" }

    Write-Host ""
    Write-Host "======================================================"
    Write-Host "KAP_FDO_AGGREGATE_TABLE_REPAIR_V1=APPLIED"
    Write-Host "KAP_FDO_SOURCE=OFFICIAL_AGGREGATE_TABLE"
    Write-Host "PER_COMPANY_GENERAL_PAGE_DEPENDENCY=REMOVED_FROM_LIVE_PATH"
    Write-Host "SINGLE_KAP_REQUEST_PER_REFRESH=YES"
    Write-Host "SAHOL_TABLE_ROW_SUPPORTED=YES"
    Write-Host "TTKOM_TABLE_ROW_SUPPORTED=YES"
    Write-Host "MULTI_ROW_SAME_SYMBOL=SUMMED"
    Write-Host "MISSING_SYMBOL=FAIL_CLOSED"
    Write-Host "FDO_CANONICAL_STORE=REUSED"
    Write-Host "AL_SAT_MUTATION=NO"
    Write-Host "CANONICAL_RANKING_MUTATION=NO"
    Write-Host "TARGET_TESTS=PASS"
    Write-Host "FULL_REGRESSION=PASS"
    Write-Host "NEXT=FINAL_LIVE_SMOKE_RETRY"
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
