param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Python sanal ortamı bulunamadı: $Python"
}

$PrebreakoutTarget = Join-Path $ProjectRoot "backend\app\prebreakout"
$UiTarget = Join-Path $ProjectRoot "backend\app\ui"

Copy-Item "$PackageRoot\backend\app\prebreakout\prebreakout_stage.py" "$PrebreakoutTarget\prebreakout_stage.py" -Force
Copy-Item "$PackageRoot\backend\app\prebreakout\prebreakout_engine.py" "$PrebreakoutTarget\prebreakout_engine.py" -Force
Copy-Item "$PackageRoot\backend\app\prebreakout\prebreakout_backtest.py" "$PrebreakoutTarget\prebreakout_backtest.py" -Force
Copy-Item "$PackageRoot\backend\app\prebreakout\prebreakout_report.py" "$PrebreakoutTarget\prebreakout_report.py" -Force
Copy-Item "$PackageRoot\backend\app\ui\prebreakout_dashboard.py" "$UiTarget\prebreakout_dashboard.py" -Force

$Tests = @(
    "test_prebreakout_momentum_gate.py",
    "test_prebreakout_performance_label.py",
    "test_prebreakout_report_performance_label.py",
    "test_prebreakout_dashboard_performance_label.py"
)

foreach ($Test in $Tests) {
    Copy-Item `
        (Join-Path $PackageRoot "backend\tests\$Test") `
        (Join-Path $ProjectRoot "backend\tests\$Test") `
        -Force
}

Set-Location $ProjectRoot

& $Python -m pytest `
    backend/tests/test_prebreakout_stage.py `
    backend/tests/test_prebreakout_engine.py `
    backend/tests/test_prebreakout_backtest.py `
    backend/tests/test_prebreakout_report.py `
    backend/tests/test_prebreakout_dashboard.py `
    backend/tests/test_prebreakout_momentum_gate.py `
    backend/tests/test_prebreakout_performance_label.py `
    backend/tests/test_prebreakout_report_performance_label.py `
    backend/tests/test_prebreakout_dashboard_performance_label.py `
    -q

if ($LASTEXITCODE -ne 0) {
    throw "Sprint-85 hedef testleri başarısız."
}

Write-Host ""
Write-Host "Sprint-85 kuruldu ve hedef testleri tamamlandı."
Write-Host "Tam regresyon komutu:"
Write-Host '& ".\.venv\Scripts\python.exe" -m pytest -q'
