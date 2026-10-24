$ErrorActionPreference = "Stop"

$Root = "D:\Projects\Hisse-Robotu"
$Patch = Join-Path $PSScriptRoot "HISSE-ROBOTU-KAP-FUND-CODE-PARSER-ROBUSTNESS-V1.patch"

if (-not (Test-Path $Root)) { throw "REPO_NOT_FOUND=$Root" }
if (-not (Test-Path $Patch)) { throw "PATCH_NOT_FOUND=$Patch" }

Set-Location $Root

Write-Host "STEP=GIT_APPLY_CHECK"
& git apply --check $Patch
if ($LASTEXITCODE -ne 0) {
    Write-Host "SOURCE_MUTATION=NO"
    throw "GIT_APPLY_CHECK_FAILED"
}

Write-Host "STEP=GIT_APPLY"
& git apply $Patch
if ($LASTEXITCODE -ne 0) { throw "GIT_APPLY_FAILED" }

$Python = if (Test-Path "$Root\.venv\Scripts\python.exe") {
    "$Root\.venv\Scripts\python.exe"
} else {
    "python"
}

$OldPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = "$Root\backend"

    Write-Host "STEP=TARGET_TESTS"
    & $Python -m pytest -q backend/tests/test_fund_kap_portfolio_ingestion_v1.py
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
Write-Host "KAP_FUND_CODE_PARSER_ROBUSTNESS=APPLIED"
Write-Host "DETACHED_FUND_NAME_EXTRACTION=SUPPORTED"
Write-Host "REPORT_TITLE_FUND_CODE_FALLBACK=SUPPORTED"
Write-Host "AP5_HAZIRAN_EXTRACTION_SHAPE=SUPPORTED"
Write-Host "TARGET_TESTS=PASS"
Write-Host "FULL_REGRESSION=PASS"
Write-Host "AL_SAT_MUTATION=NO"
Write-Host "CANONICAL_RANKING_MUTATION=NO"
Write-Host "NEXT=AP5_HAZIRAN_LIVE_RETRY"
Write-Host "==============================================="
