$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host ""
Write-Host "Sprint-46 VBTS veri bütünlüğü kuruluyor..."

python .\apply_sprint46_vbts_integrity_health.py
if ($LASTEXITCODE -ne 0) { exit 1 }

python -m pytest `
  .\backend\tests\test_dashboard_vbts_manager.py `
  .\backend\tests\test_dashboard_vbts_lifecycle.py `
  .\backend\tests\test_dashboard_vbts_operational_reliability.py `
  .\backend\tests\test_dashboard_vbts_backup_restore.py `
  .\backend\tests\test_dashboard_vbts_integrity_health.py `
  .\backend\tests\test_dashboard_vbts_management_panel.py `
  .\backend\tests\test_dashboard_vbts_lifecycle_panel.py `
  .\backend\tests\test_dashboard_vbts_operational_panel.py `
  .\backend\tests\test_dashboard_vbts_backup_restore_panel.py `
  .\backend\tests\test_dashboard_vbts_integrity_health_panel.py `
  .\backend\tests\test_sprint42_vbts_submit_button.py -q
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host ""
Write-Host "Sprint-46 kurulumu ve hızlı testleri başarılı."
