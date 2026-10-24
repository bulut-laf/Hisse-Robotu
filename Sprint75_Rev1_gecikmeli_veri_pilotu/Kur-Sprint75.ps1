param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Proje sanal ortamı bulunamadı: $python"
}

Copy-Item "$packageRoot\backend\app\data\delayed_data_pilot.py" "$ProjectRoot\backend\app\data\delayed_data_pilot.py" -Force
Copy-Item "$packageRoot\backend\dashboard.py" "$ProjectRoot\backend\dashboard.py" -Force
Copy-Item "$packageRoot\backend\tests\test_delayed_data_pilot.py" "$ProjectRoot\backend\tests\test_delayed_data_pilot.py" -Force
Copy-Item "$packageRoot\backend\tests\test_delayed_data_pilot_dashboard.py" "$ProjectRoot\backend\tests\test_delayed_data_pilot_dashboard.py" -Force

Set-Location $ProjectRoot

& $python -m pytest `
    backend/tests/test_delayed_data_pilot.py `
    backend/tests/test_delayed_data_pilot_dashboard.py `
    backend/tests/test_market_data.py `
    backend/tests/test_data_freshness.py `
    backend/tests/test_streamlit_api_compatibility.py `
    backend/tests/test_technical_analysis_v12_closeout.py -q
