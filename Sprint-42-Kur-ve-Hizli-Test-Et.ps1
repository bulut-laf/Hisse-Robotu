$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host ""
Write-Host "Sprint-42 VBTS arayüz yönetimi kuruluyor..."

python .\apply_sprint42_vbts_ui_management.py
if ($LASTEXITCODE -ne 0) { exit 1 }

python -m pytest `
  .\backend\tests\test_dashboard_vbts_manager.py `
  .\backend\tests\test_dashboard_vbts_management_panel.py -q
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host ""
Write-Host "Sprint-42 kurulumu ve hızlı testleri başarılı."
Write-Host "Tam regresyon sprint sonunda tek kez çalıştırılacaktır."
