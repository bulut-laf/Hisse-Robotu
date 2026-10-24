$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

python -m pytest `
  .\backend\tests\test_sprint_package_runner.py `
  .\backend\tests\test_sprint_package_runner_history_safety.py -q

if ($LASTEXITCODE -ne 0) {
    Write-Error "Tek komut betiği güvenlik testi başarısız oldu."
    exit 1
}

Write-Host ""
Write-Host "Tek komut betiği düzeltildi."
Write-Host "Eski apply_*.py dosyaları artık yeniden çalıştırılmayacak."
