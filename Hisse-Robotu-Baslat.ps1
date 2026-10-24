$ErrorActionPreference = "Stop"

$ProjeKoku = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjeKoku

$Python = Join-Path $ProjeKoku ".venv\Scripts\python.exe"
$Dashboard = Join-Path $ProjeKoku "backend\dashboard.py"
$Gereksinimler = Join-Path $ProjeKoku "requirements.txt"

if (-not (Test-Path $Python)) {
    Write-Host "HATA: Proje sanal ortami bulunamadi: $Python" -ForegroundColor Red
    Write-Host "Once proje klasorunde Python sanal ortamini olusturun."
    Read-Host "Kapatmak icin Enter"
    exit 1
}

if (-not (Test-Path $Dashboard)) {
    Write-Host "HATA: Streamlit paneli bulunamadi: $Dashboard" -ForegroundColor Red
    Read-Host "Kapatmak icin Enter"
    exit 1
}

& $Python -c "import numpy, pandas, yfinance, streamlit, reportlab" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "HATA: Gerekli Python paketlerinden biri eksik." -ForegroundColor Red
    Write-Host "Kurulum komutu:"
    Write-Host "  .\.venv\Scripts\python.exe -m pip install -r `"$Gereksinimler`""
    Read-Host "Kapatmak icin Enter"
    exit 1
}

Write-Host "Hisse Robotu baslatiliyor..." -ForegroundColor Green
& $Python -m streamlit run $Dashboard --server.port 8501 --browser.gatherUsageStats false
exit $LASTEXITCODE

