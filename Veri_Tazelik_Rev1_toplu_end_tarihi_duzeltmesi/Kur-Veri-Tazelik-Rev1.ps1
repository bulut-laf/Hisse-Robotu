param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Proje sanal ortamı bulunamadı: $python"
}

Copy-Item "$packageRoot\backend\app\data\batch_market_data.py" "$ProjectRoot\backend\app\data\batch_market_data.py" -Force
Copy-Item "$packageRoot\backend\tests\test_batch_market_data.py" "$ProjectRoot\backend\tests\test_batch_market_data.py" -Force

Set-Location $ProjectRoot

& $python -m pytest `
    backend/tests/test_batch_market_data.py `
    backend/tests/test_market_data.py `
    backend/tests/test_data_freshness.py `
    backend/tests/test_momentum_preflight_freshness.py `
    backend/tests/test_dashboard_market_scanner_factory.py `
    backend/tests/test_dashboard_market_scanner_source_factory.py `
    backend/tests/test_streamlit_api_compatibility.py -q
