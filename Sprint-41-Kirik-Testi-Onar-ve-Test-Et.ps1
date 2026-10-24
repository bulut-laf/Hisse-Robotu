$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host ""
Write-Host "Kırık Sprint-41 test dosyası onarılıyor..."

$Source = Join-Path $ProjectRoot "backend\tests\test_dashboard_vbts_duplicate_message.py"
if (-not (Test-Path -LiteralPath $Source)) {
    Write-Error "Onarım test dosyası pakette bulunamadı."
    exit 1
}

python -m py_compile .\backend\tests\test_dashboard_vbts_duplicate_message.py
if ($LASTEXITCODE -ne 0) { exit 1 }

python -m pytest `
  .\backend\tests\test_dashboard_vbts_duplicate_message.py `
  .\backend\tests\test_dashboard_manual_vbts_status_panel.py `
  .\backend\tests\test_dashboard_source_aware_vbts_status.py -q
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host ""
Write-Host "Sprint-41 test dosyası onarıldı ve hızlı test başarılı."
