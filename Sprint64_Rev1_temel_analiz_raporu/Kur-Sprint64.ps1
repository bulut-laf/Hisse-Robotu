param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Proje sanal ortamı bulunamadı: $python"
}

New-Item -ItemType Directory -Path "$ProjectRoot\backend\app\reporting" -Force | Out-Null

Copy-Item "$packageRoot\backend\app\reporting\__init__.py" "$ProjectRoot\backend\app\reporting\__init__.py" -Force
Copy-Item "$packageRoot\backend\app\reporting\fundamental_report.py" "$ProjectRoot\backend\app\reporting\fundamental_report.py" -Force
Copy-Item "$packageRoot\backend\dashboard.py" "$ProjectRoot\backend\dashboard.py" -Force
Copy-Item "$packageRoot\backend\tests\test_fundamental_report.py" "$ProjectRoot\backend\tests\test_fundamental_report.py" -Force
Copy-Item "$packageRoot\backend\tests\test_fundamental_report_dashboard.py" "$ProjectRoot\backend\tests\test_fundamental_report_dashboard.py" -Force

Set-Location $ProjectRoot

& $python -m pytest `
    backend/tests/test_fundamental_report.py `
    backend/tests/test_fundamental_report_dashboard.py `
    backend/tests/test_fundamental_dashboard.py `
    backend/tests/test_fundamental_quality_dashboard.py `
    backend/tests/test_fundamental_score_history_dashboard.py `
    backend/tests/test_sector_reference_dashboard.py `
    backend/tests/test_sector_score_ranking_dashboard.py `
    backend/tests/test_sector_strength_dashboard.py `
    backend/tests/test_streamlit_api_compatibility.py -q
