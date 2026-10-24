$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

python .\apply_sprint42_vbts_submit_button_fix.py
if ($LASTEXITCODE -ne 0) { exit 1 }

python -m pytest `
  .\backend\tests\test_dashboard_vbts_manager.py `
  .\backend\tests\test_dashboard_vbts_management_panel.py `
  .\backend\tests\test_sprint42_vbts_ui_repair.py `
  .\backend\tests\test_sprint42_vbts_submit_button.py -q
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host ""
Write-Host "Sprint-42 VBTS düğme düzeltmesi ve hızlı testler başarılı."
