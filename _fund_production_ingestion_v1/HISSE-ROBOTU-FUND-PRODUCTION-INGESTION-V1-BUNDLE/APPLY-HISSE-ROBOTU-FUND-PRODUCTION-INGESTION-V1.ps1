$ErrorActionPreference = "Stop"

$Root = "D:\Projects\Hisse-Robotu"
$Patch = Join-Path $PSScriptRoot "HISSE-ROBOTU-FUND-PRODUCTION-INGESTION-V1.patch"

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

Write-Host "STEP=PYPDF_DEPENDENCY"
& $Python -c "import pypdf; print('PYPDF_VERSION=' + pypdf.__version__)"
if ($LASTEXITCODE -ne 0) {
    & $Python -m pip install "pypdf>=5,<7"
    if ($LASTEXITCODE -ne 0) {
        throw "PYPDF_INSTALL_FAILED"
    }
}

$OldPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = "$Root\backend"

    Write-Host "STEP=TARGET_TESTS"
    & $Python -m pytest -q `
        backend/tests/test_fund_kap_portfolio_ingestion_v1.py `
        backend/tests/test_fund_portfolio_tracking_v1.py `
        backend/tests/test_fund_analysis_center_ui_v1.py `
        backend/tests/test_fund_pressure_risk_v1.py `
        backend/tests/test_fund_risk_metrics_v1.py
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
Write-Host "KAP_OFFICIAL_PORTFOLIO_INGESTION=APPLIED"
Write-Host "EXPLICIT_KAP_DETAIL_URL_INGEST=READY"
Write-Host "KAP_PDF_EQUITY_PARSER=READY"
Write-Host "MONTH_END_PORTFOLIO_DATE=GUARDED"
Write-Host "PUBLICATION_DATE=GUARDED"
Write-Host "APPEND_ONLY_SNAPSHOT_STORE=REUSED"
Write-Host "DUPLICATE_INGESTION=IDEMPOTENT"
Write-Host "AMBIGUOUS_ATTACHMENT=FAIL_CLOSED"
Write-Host "AUTOMATIC_KAP_CRAWLING=NO"
Write-Host "TARGET_TESTS=PASS"
Write-Host "FULL_REGRESSION=PASS"
Write-Host "AL_SAT_MUTATION=NO"
Write-Host "CANONICAL_RANKING_MUTATION=NO"
Write-Host "NEXT=LIVE_KAP_PORTFOLIO_SMOKE"
Write-Host "==============================================="
