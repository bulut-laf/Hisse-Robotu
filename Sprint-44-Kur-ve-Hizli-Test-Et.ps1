$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host ""
Write-Host "Sprint-44 VBTS operasyonel güvenilirlik kuruluyor..."

python .\apply_sprint44_vbts_operational_reliability.py
if ($LASTEXITCODE -ne 0) { exit 1 }

python -m pytest `
  .\backend\tests\test_dashboard_vbts_manager.py `
  .\backend\tests\test_dashboard_vbts_lifecycle.py `
  .\backend\tests\test_dashboard_vbts_operational_reliability.py `
  .\backend\tests\test_dashboard_vbts_management_panel.py `
  .\backend\tests\test_dashboard_vbts_lifecycle_panel.py `
  .\backend\tests\test_dashboard_vbts_operational_panel.py `
  .\backend\tests\test_sprint42_vbts_submit_button.py -q
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host ""
Write-Host "Sprint-44 kurulumu ve hızlı testleri başarılı."
