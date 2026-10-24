param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Python sanal ortamı bulunamadı: $Python"
}

$UiTarget = Join-Path $ProjectRoot "backend\app\ui"
New-Item -ItemType Directory -Path $UiTarget -Force | Out-Null

Copy-Item `
    "$PackageRoot\backend\app\ui\prebreakout_dashboard.py" `
    "$UiTarget\prebreakout_dashboard.py" `
    -Force

$Tests = @(
    "test_prebreakout_dashboard.py",
    "test_dashboard_prebreakout_integration.py"
)

foreach ($Test in $Tests) {
    Copy-Item `
        (Join-Path $PackageRoot "backend\tests\$Test") `
        (Join-Path $ProjectRoot "backend\tests\$Test") `
        -Force
}

& $Python "$PackageRoot\patch_dashboard_sprint84.py" $ProjectRoot

Set-Location $ProjectRoot

& $Python -m pytest `
    backend/tests/test_prebreakout_dashboard.py `
    backend/tests/test_dashboard_prebreakout_integration.py `
    backend/tests/test_prebreakout_engine.py `
    backend/tests/test_prebreakout_backtest.py `
    backend/tests/test_streamlit_api_compatibility.py `
    -q

if ($LASTEXITCODE -ne 0) {
    throw "Sprint-84 hedef testleri başarısız."
}

Write-Host ""
Write-Host "Sprint-84 kuruldu ve hedef testleri tamamlandı."
Write-Host "Tam regresyon komutu:"
Write-Host '& ".\.venv\Scripts\python.exe" -m pytest -q'
