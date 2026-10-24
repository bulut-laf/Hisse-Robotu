$ErrorActionPreference = "Stop"

$Root = "D:\Projects\Hisse-Robotu"
$Patch = Join-Path $PSScriptRoot "HISSE-ROBOTU-FUND-AUTO-DISCOVERY-AUTO-INGESTION-V1.patch"

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
        backend\tests\test_fund_kap_portfolio_ingestion_v1.py `
        backend\tests\test_fund_kap_portfolio_auto_ingestion_v1.py `
        backend\tests\test_fund_analysis_center_ui_v1.py `
        backend\tests\test_fund_analysis_non_blocking_entry_v1.py

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
    Write-Host "FUND_PORTFOLIO_AUTO_DISCOVERY_AUTO_INGESTION_V1=APPLIED"
    Write-Host "KAP_DISCLOSURE_DISCOVERY=AUTO"
    Write-Host "KNOWN_FUND_UNIVERSE_FILTER=READY"
    Write-Host "DETAIL_URL_RESOLUTION=AUTO"
    Write-Host "ATTACHMENT_DISCOVERY=AUTO"
    Write-Host "PDF_DOWNLOAD=AUTO"
    Write-Host "WRAPPED_PDF_EXTRACTION=AUTO"
    Write-Host "FUND_CODE_PARSE=AUTO"
    Write-Host "REPORT_PERIOD_PARSE=AUTO"
    Write-Host "PUBLICATION_DATE_PARSE=AUTO"
    Write-Host "SNAPSHOT_INGESTION=AUTO"
    Write-Host "DUPLICATE_GUARD=YES"
    Write-Host "FAILURE_ISOLATION=YES"
    Write-Host "MANUAL_PDF=FALLBACK_ONLY"
    Write-Host "INITIAL_PAGE_NETWORK_CALL=NO"
    Write-Host "AL_SAT_MUTATION=NO"
    Write-Host "CANONICAL_RANKING_MUTATION=NO"
    Write-Host "TARGET_TESTS=PASS"
    Write-Host "FULL_REGRESSION=PASS"
    Write-Host "NEXT=LIVE_AUTO_DISCOVERY_SMOKE"
    Write-Host "==============================================="
}
catch {
    if ($Applied) {
        Write-Host "ROLLBACK=START"
        git apply -R --whitespace=nowarn $Patch
        if ($LASTEXITCODE -eq 0) {
            Write-Host "ROLLBACK=PASS"
        }
        else {
            Write-Host "ROLLBACK=FAILED"
        }
    }
    throw
}
