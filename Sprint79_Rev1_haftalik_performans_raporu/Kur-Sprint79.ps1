param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Proje sanal ortamı bulunamadı: $python"
}

Copy-Item "$packageRoot\backend\app\analysis\weekly_performance_report.py" "$ProjectRoot\backend\app\analysis\weekly_performance_report.py" -Force
Copy-Item "$packageRoot\backend\dashboard.py" "$ProjectRoot\backend\dashboard.py" -Force
Copy-Item "$packageRoot\backend\tests\test_weekly_performance_report.py" "$ProjectRoot\backend\tests\test_weekly_performance_report.py" -Force
Copy-Item "$packageRoot\backend\tests\test_weekly_performance_report_dashboard.py" "$ProjectRoot\backend\tests\test_weekly_performance_report_dashboard.py" -Force

Set-Location $ProjectRoot

& $python -m pytest `
    backend/tests/test_weekly_performance_report.py `
    backend/tests/test_weekly_performance_report_dashboard.py `
    backend/tests/test_shadow_portfolio.py `
    backend/tests/test_shadow_portfolio_dashboard.py `
    backend/tests/test_daily_operation_panel_shadow.py `
    backend/tests/test_streamlit_api_compatibility.py -q
