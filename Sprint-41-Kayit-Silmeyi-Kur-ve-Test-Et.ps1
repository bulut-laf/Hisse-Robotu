$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

python .\apply_sprint41_vbts_delete.py
if ($LASTEXITCODE -ne 0) { exit 1 }

python -m pytest `
  .\backend\tests\test_vbts_quick_prepare_script.py `
  .\backend\tests\test_vbts_quick_prepare_trim.py `
  .\backend\tests\test_vbts_quick_prepare_delete.py -q
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host ""
Write-Host "Sprint-41 kayıt silme desteği ve hızlı test başarılı."
