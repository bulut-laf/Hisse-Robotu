$ErrorActionPreference = "Stop"

$Root = "D:\Projects\Hisse-Robotu"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Patch = Join-Path $Here "HISSE-ROBOTU-FUND-KAP-MANUAL-PDF-INGESTION-V1.patch"

if (-not (Test-Path $Root)) { throw "REPO_NOT_FOUND=$Root" }
if (-not (Test-Path $Patch)) { throw "PATCH_NOT_FOUND=$Patch" }

Set-Location $Root

$Python = if (Test-Path "$Root\.venv\Scripts\python.exe") {
    "$Root\.venv\Scripts\python.exe"
} else {
    "python"
}

Write-Host "STEP=GIT_APPLY_CHECK"
git apply --check $Patch
if ($LASTEXITCODE -ne 0) { throw "GIT_APPLY_CHECK_FAILED" }

Write-Host "STEP=GIT_APPLY"
git apply $Patch
if ($LASTEXITCODE -ne 0) { throw "GIT_APPLY_FAILED" }

$OldPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = "$Root\backend"

    Write-Host "STEP=TARGET_TESTS"
    & $Python -m pytest -q `
        backend/tests/test_fund_kap_portfolio_ingestion_v1.py `
        backend/tests/test_fund_analysis_center_ui_v1.py `
        backend/tests/test_fund_analysis_non_blocking_entry_v1.py `
        backend/tests/test_fund_portfolio_tracking_v1.py
    if ($LASTEXITCODE -ne 0) { throw "TARGET_TESTS_FAILED" }

    Write-Host "STEP=FULL_REGRESSION"
    & $Python -m pytest -q backend/tests
    if ($LASTEXITCODE -ne 0) { throw "FULL_REGRESSION_FAILED" }
}
finally {
    $env:PYTHONPATH = $OldPythonPath
}

Write-Host ""
Write-Host "==============================================="
Write-Host "FUND_KAP_MANUAL_PDF_INGESTION=APPLIED"
Write-Host "KAP_URL_FETCH=OPTIONAL"
Write-Host "MANUAL_PORTFOLIO_PDF_UPLOAD=READY"
Write-Host "NOTIFICATION_PAGE_PRINT=REJECTED"
Write-Host "REPORT_PERIOD_EXPLICIT=YES"
Write-Host "PUBLICATION_DATE_EXPLICIT=YES"
Write-Host "APPEND_ONLY_SNAPSHOT_STORE=REUSED"
Write-Host "IDEMPOTENT_SAME_CONTENT=YES"
Write-Host "TARGET_TESTS=PASS"
Write-Host "FULL_REGRESSION=PASS"
Write-Host "AL_SAT_MUTATION=NO"
Write-Host "CANONICAL_RANKING_MUTATION=NO"
Write-Host "NEXT=MANUAL_PDF_LIVE_SMOKE"
Write-Host "==============================================="
