$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

python .\apply_sprint41_vbts_test_scope_fix.py
if ($LASTEXITCODE -ne 0) { exit 1 }

python -m pytest `
  .\backend\tests\test_dashboard_vbts_duplicate_message.py `
  .\backend\tests\test_dashboard_manual_vbts_status_panel.py `
  .\backend\tests\test_dashboard_source_aware_vbts_status.py -q
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host ""
Write-Host "Sprint-41 test kapsamı düzeltmesi ve hızlı test başarılı."
