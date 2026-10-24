param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Proje sanal ortamı bulunamadı: $python"
}

Copy-Item "$packageRoot\backend\app\reporting\fundamental_report_archive.py" "$ProjectRoot\backend\app\reporting\fundamental_report_archive.py" -Force
Copy-Item "$packageRoot\backend\dashboard.py" "$ProjectRoot\backend\dashboard.py" -Force
Copy-Item "$packageRoot\backend\tests\test_fundamental_report_archive_filter.py" "$ProjectRoot\backend\tests\test_fundamental_report_archive_filter.py" -Force
Copy-Item "$packageRoot\backend\tests\test_fundamental_report_archive_filter_dashboard.py" "$ProjectRoot\backend\tests\test_fundamental_report_archive_filter_dashboard.py" -Force

Set-Location $ProjectRoot

& $python -m pytest `
    backend/tests/test_fundamental_report_archive_filter.py `
    backend/tests/test_fundamental_report_archive_filter_dashboard.py `
    backend/tests/test_fundamental_report_archive.py `
    backend/tests/test_fundamental_report_archive_dashboard.py `
    backend/tests/test_fundamental_report.py `
    backend/tests/test_fundamental_report_dashboard.py `
    backend/tests/test_streamlit_api_compatibility.py -q
