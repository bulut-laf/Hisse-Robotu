$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

python -m py_compile .\backend\tests\test_sprint_package_runner.py
if ($LASTEXITCODE -ne 0) { exit 1 }

python -m pytest `
  .\backend\tests\test_sprint_package_runner.py `
  .\backend\tests\test_sprint_package_runner_history_safety.py -q
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host ""
Write-Host "Sprint-40 çalıştırıcı testleri yeni güvenli davranışa uyarlandı."
