param(
    [string]$ProjectRoot = (Get-Location).Path
)
$ErrorActionPreference = "Stop"
if (-not (Test-Path (Join-Path $ProjectRoot "backend\dashboard.py"))) {
    throw "Proje kökü bulunamadı: backend\dashboard.py yok."
}
$packageRoot = $PSScriptRoot
$target = Join-Path $ProjectRoot "backend\app\funds\hedef24_store.py"
$targetDir = Split-Path $target -Parent
New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
if (Test-Path $target) {
    Copy-Item $target "$target.bak_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
}
Copy-Item (Join-Path $packageRoot "hedef24\store.py") $target -Force

$testTarget = Join-Path $ProjectRoot "backend\tests\test_hedef24_store_sprint2.py"
if (Test-Path $testTarget) {
    Copy-Item $testTarget "$testTarget.bak_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
}
Copy-Item (Join-Path $packageRoot "tests\test_store.py") $testTarget -Force

$seed = Join-Path $ProjectRoot "_discovery\erste_hungary\hedef24_portfolio_seed.json"
if (-not (Test-Path $seed)) {
    throw "Başlangıç verisi bulunamadı: $seed. Önce Sprint 1 kurulumunu tamamlayın."
}
$env:PYTHONPATH = $ProjectRoot
$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "Python venv bulunamadı: $python" }

Write-Host "Sprint 2 modülü ve hedef testleri kopyalandı."
Write-Host "Bu betik dashboard.py dosyasını değiştirmez."
Write-Host "Sonraki doğrulama komutları:"
Write-Host ".\.venv\Scripts\python.exe -m py_compile backend\app\funds\hedef24_store.py"
Write-Host ".\.venv\Scripts\python.exe -m pytest backend\tests\test_hedef24_store_sprint2.py -q"
