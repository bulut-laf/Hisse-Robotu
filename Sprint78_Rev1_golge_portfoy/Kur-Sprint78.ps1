param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Proje sanal ortamı bulunamadı: $python"
}

Copy-Item "$packageRoot\backend\app\analysis\shadow_portfolio.py" "$ProjectRoot\backend\app\analysis\shadow_portfolio.py" -Force
Copy-Item "$packageRoot\backend\app\analysis\daily_operation_panel.py" "$ProjectRoot\backend\app\analysis\daily_operation_panel.py" -Force
Copy-Item "$packageRoot\backend\dashboard.py" "$ProjectRoot\backend\dashboard.py" -Force
Copy-Item "$packageRoot\backend\tests\test_shadow_portfolio.py" "$ProjectRoot\backend\tests\test_shadow_portfolio.py" -Force
Copy-Item "$packageRoot\backend\tests\test_shadow_portfolio_dashboard.py" "$ProjectRoot\backend\tests\test_shadow_portfolio_dashboard.py" -Force
Copy-Item "$packageRoot\backend\tests\test_daily_operation_panel_shadow.py" "$ProjectRoot\backend\tests\test_daily_operation_panel_shadow.py" -Force

Set-Location $ProjectRoot

& $python -m pytest `
    backend/tests/test_shadow_portfolio.py `
    backend/tests/test_shadow_portfolio_dashboard.py `
    backend/tests/test_daily_operation_panel_shadow.py `
    backend/tests/test_daily_operation_panel.py `
    backend/tests/test_daily_operation_panel_dashboard.py `
    backend/tests/test_automatic_signal_tracking.py `
    backend/tests/test_automatic_signal_tracking_dashboard.py `
    backend/tests/test_signal_outcome_tracking.py `
    backend/tests/test_streamlit_api_compatibility.py -q
