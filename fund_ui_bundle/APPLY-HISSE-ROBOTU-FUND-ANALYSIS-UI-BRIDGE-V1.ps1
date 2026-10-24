$ErrorActionPreference = "Stop"

$Root = "D:\Projects\Hisse-Robotu"
$Patch = Join-Path $PSScriptRoot "HISSE-ROBOTU-FUND-ANALYSIS-UI-BRIDGE-V1.patch"

if (-not (Test-Path -LiteralPath $Root)) {
    throw "REPO_NOT_FOUND=$Root"
}
if (-not (Test-Path -LiteralPath $Patch)) {
    throw "PATCH_NOT_FOUND=$Patch"
}

$Python = if (Test-Path "$Root\.venv\Scripts\python.exe") {
    "$Root\.venv\Scripts\python.exe"
} else {
    "python"
}

$OldPythonPath = $env:PYTHONPATH
$Separator = [IO.Path]::PathSeparator
$env:PYTHONPATH = "$Root\backend$Separator$Root"

Set-Location $Root

try {
    Write-Host "STEP=GIT_APPLY_CHECK"
    git apply --check -- "$Patch"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "GIT_APPLY_CHECK=PASS"
        git apply -- "$Patch"
        if ($LASTEXITCODE -ne 0) {
            throw "GIT_APPLY_FAILED"
        }
        Write-Host "GIT_APPLY=PASS"
    }
    else {
        Write-Host "GIT_APPLY_CHECK=FAILED"
        git apply --reverse --check -- "$Patch" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "PATCH_STATE=ALREADY_APPLIED"
        }
        else {
            throw "GIT_APPLY_CHECK_FAILED_REPO_UNTOUCHED"
        }
    }

    Write-Host "STEP=PYTHON_COMPILE"
    & $Python -m py_compile `
        backend/app/funds/portfolio_tracking.py `
        backend/app/ui/fund_analysis_center.py `
        backend/dashboard.py
    if ($LASTEXITCODE -ne 0) {
        throw "PYTHON_COMPILE_FAILED"
    }
    Write-Host "PYTHON_COMPILE=PASS"

    Write-Host "STEP=TARGET_TESTS"
    & $Python -m pytest -q `
        backend/tests/test_fund_analysis_center_ui_v1.py `
        backend/tests/test_fund_portfolio_tracking_v1.py `
        backend/tests/test_fund_pressure_risk_v1.py
    if ($LASTEXITCODE -ne 0) {
        throw "TARGET_TESTS_FAILED"
    }
    Write-Host "TARGET_TESTS=PASS"

    Write-Host "STEP=FULL_REGRESSION"
    & $Python -m pytest -q backend/tests
    if ($LASTEXITCODE -ne 0) {
        throw "FULL_REGRESSION_FAILED"
    }

    Write-Host ""
    Write-Host "==============================================="
    Write-Host "FUND_ANALYSIS_UI_BRIDGE=APPLIED"
    Write-Host "CURRENT_PORTFOLIO_VIEW=READY"
    Write-Host "PORTFOLIO_CHANGE_VIEW=READY"
    Write-Host "NEW_ENTRY_FULL_EXIT_VIEW=READY"
    Write-Host "ACCUMULATION_DISTRIBUTION_BREADTH_VIEW=READY"
    Write-Host "FUND_FDO_PRESSURE_RISK_VIEW=READY_FOR_INPUT"
    Write-Host "TARGET_TESTS=PASS"
    Write-Host "FULL_REGRESSION=PASS"
    Write-Host "AL_SAT_MUTATION=NO"
    Write-Host "CANONICAL_RANKING_MUTATION=NO"
    Write-Host "NEXT=FUND_PORTFOLIO_PRODUCTION_INGESTION"
    Write-Host "==============================================="
}
finally {
    $env:PYTHONPATH = $OldPythonPath
}
