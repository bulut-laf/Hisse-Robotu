$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host ""
Write-Host "Sprint-43 VBTS yaşam döngüsü kuruluyor..."

python .\apply_sprint43_vbts_lifecycle.py
if ($LASTEXITCODE -ne 0) { exit 1 }

python -m pytest `
  .\backend\tests\test_dashboard_vbts_manager.py `
  .\backend\tests\test_dashboard_vbts_lifecycle.py `
  .\backend\tests\test_dashboard_vbts_management_panel.py `
  .\backend\tests\test_dashboard_vbts_lifecycle_panel.py `
  .\backend\tests\test_sprint42_vbts_submit_button.py -q
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host ""
Write-Host "Sprint-43 kurulumu ve hızlı testleri başarılı."
Write-Host "Tam regresyon sprint sonunda tek kez çalıştırılacaktır."
