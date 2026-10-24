param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Python sanal ortamı bulunamadı: $Python"
}

$ModuleTarget = Join-Path $ProjectRoot "backend\app\prebreakout"
New-Item -ItemType Directory -Path $ModuleTarget -Force | Out-Null

Copy-Item `
    "$PackageRoot\backend\app\prebreakout\prebreakout_backtest.py" `
    "$ModuleTarget\prebreakout_backtest.py" `
    -Force

Copy-Item `
    "$PackageRoot\backend\app\prebreakout\prebreakout_report.py" `
    "$ModuleTarget\prebreakout_report.py" `
    -Force

$Tests = @(
    "test_prebreakout_backtest.py",
    "test_prebreakout_report.py",
    "test_prebreakout_no_lookahead.py"
)

foreach ($Test in $Tests) {
    Copy-Item `
        (Join-Path $PackageRoot "backend\tests\$Test") `
        (Join-Path $ProjectRoot "backend\tests\$Test") `
        -Force
}

Set-Location $ProjectRoot

& $Python -m pytest `
    backend/tests/test_prebreakout_backtest.py `
    backend/tests/test_prebreakout_report.py `
    backend/tests/test_prebreakout_no_lookahead.py `
    -q

if ($LASTEXITCODE -ne 0) {
    throw "Sprint-83 hedef testleri başarısız."
}

Write-Host ""
Write-Host "Sprint-83 kuruldu ve hedef testleri tamamlandı."
Write-Host "Sonraki komut:"
Write-Host '& ".\.venv\Scripts\python.exe" -m pytest -q'
