param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Python sanal ortamı bulunamadı: $Python"
}

$Target = Join-Path $ProjectRoot "backend\app\prebreakout"
New-Item -ItemType Directory -Path $Target -Force | Out-Null

Copy-Item "$PackageRoot\backend\app\prebreakout\prebreakout_validation.py" "$Target\prebreakout_validation.py" -Force
Copy-Item "$PackageRoot\backend\app\prebreakout\prebreakout_validation_report.py" "$Target\prebreakout_validation_report.py" -Force

$Tests = @(
    "test_prebreakout_validation.py",
    "test_prebreakout_validation_no_lookahead.py",
    "test_prebreakout_validation_report.py"
)

foreach ($Test in $Tests) {
    Copy-Item `
        (Join-Path $PackageRoot "backend\tests\$Test") `
        (Join-Path $ProjectRoot "backend\tests\$Test") `
        -Force
}

Set-Location $ProjectRoot

& $Python -m pytest `
    backend/tests/test_prebreakout_validation.py `
    backend/tests/test_prebreakout_validation_no_lookahead.py `
    backend/tests/test_prebreakout_validation_report.py `
    backend/tests/test_prebreakout_momentum_gate.py `
    backend/tests/test_prebreakout_performance_label.py `
    -q

if ($LASTEXITCODE -ne 0) {
    throw "Sprint-86 hedef testleri başarısız."
}

Write-Host ""
Write-Host "Sprint-86 kuruldu ve hedef testleri tamamlandı."
Write-Host "Tam regresyon komutu:"
Write-Host '& ".\.venv\Scripts\python.exe" -m pytest -q'
