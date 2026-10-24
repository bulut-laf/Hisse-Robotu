$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

python .\apply_sprint41_vbts_trim_fix.py
if ($LASTEXITCODE -ne 0) { exit 1 }

python -m pytest `
  .\backend\tests\test_vbts_quick_prepare_script.py `
  .\backend\tests\test_vbts_quick_prepare_trim.py -q
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host ""
Write-Host "Sprint-41 giriş boşluğu düzeltmesi ve hızlı test başarılı."
