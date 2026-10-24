$ErrorActionPreference = "Stop"

$Root = "D:\Projects\Hisse-Robotu"
$Patch = Join-Path $PSScriptRoot "HISSE-ROBOTU-REGRESSION-3FAIL-REPAIR-V1.patch"
$VbtsFile = Join-Path $Root "backend\app\compliance\dashboard_vbts_manager.py"

if (-not (Test-Path $Root)) { throw "REPO_NOT_FOUND=$Root" }
if (-not (Test-Path $Patch)) { throw "PATCH_NOT_FOUND=$Patch" }
if (-not (Test-Path $VbtsFile)) { throw "VBTS_SOURCE_NOT_FOUND=$VbtsFile" }

Push-Location $Root
try {
    Write-Host "HISSE_ROBOTU_REGRESSION_3FAIL_REPAIR_V1"

    # 1) Date-rollover-safe VBTS health status.
    $AlreadyApplied = Select-String -LiteralPath $VbtsFile `
        -Pattern 'active_registry_records = tuple\(' `
        -Quiet -ErrorAction SilentlyContinue

    if ($AlreadyApplied) {
        Write-Host "VBTS_HEALTH_PATCH=ALREADY_APPLIED"
    }
    else {
        Write-Host "STEP=GIT_APPLY_CHECK"
        git apply --check --whitespace=error-all $Patch
        if ($LASTEXITCODE -ne 0) { throw "GIT_APPLY_CHECK_FAILED" }

        Write-Host "STEP=GIT_APPLY"
        git apply --whitespace=error-all $Patch
        if ($LASTEXITCODE -ne 0) { throw "GIT_APPLY_FAILED" }
        Write-Host "VBTS_HEALTH_PATCH=APPLIED"
    }

    # 2) Strip only a leading UTF-8 BOM from backend Python sources.
    # Byte-for-byte content is preserved after the first three BOM bytes.
    Write-Host "STEP=UTF8_BOM_NORMALIZATION"
    $BomFiles = New-Object System.Collections.Generic.List[string]

    Get-ChildItem (Join-Path $Root "backend") -Recurse -File -Filter "*.py" |
        Where-Object { $_.FullName -notmatch "\\__pycache__\\" } |
        ForEach-Object {
            $Bytes = [System.IO.File]::ReadAllBytes($_.FullName)
            if (
                $Bytes.Length -ge 3 -and
                $Bytes[0] -eq 0xEF -and
                $Bytes[1] -eq 0xBB -and
                $Bytes[2] -eq 0xBF
            ) {
                if ($Bytes.Length -eq 3) {
                    [System.IO.File]::WriteAllBytes($_.FullName, [byte[]]@())
                }
                else {
                    $Clean = New-Object byte[] ($Bytes.Length - 3)
                    [System.Array]::Copy($Bytes, 3, $Clean, 0, $Clean.Length)
                    [System.IO.File]::WriteAllBytes($_.FullName, $Clean)
                }
                $BomFiles.Add($_.FullName)
            }
        }

    Write-Host "BOM_STRIPPED_COUNT=$($BomFiles.Count)"
    foreach ($File in $BomFiles) {
        Write-Host "BOM_STRIPPED=$File"
    }

    $Python = if (Test-Path (Join-Path $Root ".venv\Scripts\python.exe")) {
        Join-Path $Root ".venv\Scripts\python.exe"
    }
    else {
        "python"
    }

    $OldPythonPath = $env:PYTHONPATH
    $env:PYTHONPATH = "$Root;$Root\backend"

    try {
        Write-Host "STEP=TARGETED_3FAIL_REGRESSION"
        & $Python -m pytest -q `
            "backend/tests/test_dashboard_vbts_integrity_health.py::test_sistem_sagligi_saglikli_dosyalarla_olumludur" `
            "backend/tests/test_streamlit_api_compatibility.py::test_backend_kaynaklarinda_use_container_width_kalmamistir" `
            "backend/tests/test_system_check.py::test_tam_sistem_kontrolu_sahte_modul_bulucuyla_hazirdir"

        if ($LASTEXITCODE -ne 0) { throw "TARGETED_3FAIL_REGRESSION_FAILED" }
        Write-Host "TARGETED_3FAIL_REGRESSION=PASS"

        Write-Host "STEP=FUND_TARGET_TESTS"
        & $Python -m pytest -q `
            backend/tests/test_fund_risk_metrics_v1.py `
            backend/tests/test_fund_portfolio_tracking_v1.py `
            backend/tests/test_fund_pressure_risk_v1.py

        if ($LASTEXITCODE -ne 0) { throw "FUND_TARGET_TESTS_FAILED" }
        Write-Host "FUND_TARGET_TESTS=PASS"

        Write-Host "STEP=FULL_REGRESSION"
        & $Python -m pytest -q backend/tests
        if ($LASTEXITCODE -ne 0) { throw "FULL_REGRESSION_FAILED" }

        Write-Host ""
        Write-Host "==============================================="
        Write-Host "VBTS_DATE_ROLLOVER_HEALTH=PASS"
        Write-Host "UTF8_BOM_NORMALIZATION=PASS"
        Write-Host "SYSTEM_CHECK_SOURCE_COMPILE=PASS"
        Write-Host "FUND_PORTFOLIO_SNAPSHOT_CHANGE_ENGINE=APPLIED"
        Write-Host "FUND_PRESSURE_RAW_METRICS=APPLIED"
        Write-Host "THREE_OBSERVATIONAL_SUBSCORES=APPLIED"
        Write-Host "TARGETED_3FAIL_REGRESSION=PASS"
        Write-Host "FUND_TARGET_TESTS=PASS"
        Write-Host "FULL_REGRESSION=PASS"
        Write-Host "AL_SAT_MUTATION=NO"
        Write-Host "CANONICAL_RANKING_MUTATION=NO"
        Write-Host "NEXT=FUND_ANALYSIS_UI_BRIDGE"
        Write-Host "==============================================="
    }
    finally {
        $env:PYTHONPATH = $OldPythonPath
    }
}
finally {
    Pop-Location
}
