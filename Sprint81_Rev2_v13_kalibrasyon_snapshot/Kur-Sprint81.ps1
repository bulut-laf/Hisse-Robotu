param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Proje sanal ortamı bulunamadı: $python"
}

Copy-Item "$packageRoot\backend\app\analysis\v13_calibration_closeout.py" "$ProjectRoot\backend\app\analysis\v13_calibration_closeout.py" -Force
Copy-Item "$packageRoot\backend\dashboard.py" "$ProjectRoot\backend\dashboard.py" -Force
Copy-Item "$packageRoot\backend\tests\test_v13_calibration_closeout.py" "$ProjectRoot\backend\tests\test_v13_calibration_closeout.py" -Force
Copy-Item "$packageRoot\backend\tests\test_v13_calibration_closeout_dashboard.py" "$ProjectRoot\backend\tests\test_v13_calibration_closeout_dashboard.py" -Force
Copy-Item "$packageRoot\backend\tests\test_v13_closeout_documentation.py" "$ProjectRoot\backend\tests\test_v13_closeout_documentation.py" -Force
Copy-Item "$packageRoot\PROJECT_NOTES.md" "$ProjectRoot\PROJECT_NOTES.md" -Force
Copy-Item "$packageRoot\KULLANIM_KILAVUZU.md" "$ProjectRoot\KULLANIM_KILAVUZU.md" -Force
Copy-Item "$packageRoot\Olustur-V13-Snapshot.ps1" "$ProjectRoot\Olustur-V13-Snapshot.ps1" -Force

Set-Location $ProjectRoot

& $python -m pytest `
    backend/tests/test_v13_calibration_closeout.py `
    backend/tests/test_v13_calibration_closeout_dashboard.py `
    backend/tests/test_v13_closeout_documentation.py `
    backend/tests/test_delayed_data_pilot.py `
    backend/tests/test_daily_operation_panel.py `
    backend/tests/test_automatic_signal_tracking.py `
    backend/tests/test_shadow_portfolio.py `
    backend/tests/test_weekly_performance_report.py `
    backend/tests/test_success_comparison_report.py `
    backend/tests/test_streamlit_api_compatibility.py -q
