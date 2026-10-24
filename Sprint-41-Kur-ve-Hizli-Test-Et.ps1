$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host ""
Write-Host "Sprint-41 hızlı kurulum testi başlatılıyor..."

python -m pytest .\backend\tests\test_vbts_quick_prepare_script.py -q

if ($LASTEXITCODE -ne 0) {
    Write-Error "Sprint-41 hedef testi başarısız oldu."
    exit 1
}

Write-Host ""
Write-Host "Sprint-41 kurulumu ve hedef testi başarılı."
Write-Host "Tam regresyon sprint sonunda çalıştırılacaktır."
