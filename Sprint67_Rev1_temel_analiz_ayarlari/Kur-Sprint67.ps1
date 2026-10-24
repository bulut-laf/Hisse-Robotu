param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Proje sanal ortamı bulunamadı: $python"
}

Copy-Item "$packageRoot\backend\app\data\fundamental_settings.py" "$ProjectRoot\backend\app\data\fundamental_settings.py" -Force
Copy-Item "$packageRoot\backend\app\analysis\sector_score_ranking.py" "$ProjectRoot\backend\app\analysis\sector_score_ranking.py" -Force
Copy-Item "$packageRoot\backend\app\analysis\sector_strength_map.py" "$ProjectRoot\backend\app\analysis\sector_strength_map.py" -Force
Copy-Item "$packageRoot\backend\dashboard.py" "$ProjectRoot\backend\dashboard.py" -Force
Copy-Item "$packageRoot\backend\tests\test_fundamental_settings.py" "$ProjectRoot\backend\tests\test_fundamental_settings.py" -Force
Copy-Item "$packageRoot\backend\tests\test_fundamental_settings_integration.py" "$ProjectRoot\backend\tests\test_fundamental_settings_integration.py" -Force
Copy-Item "$packageRoot\backend\tests\test_fundamental_settings_dashboard.py" "$ProjectRoot\backend\tests\test_fundamental_settings_dashboard.py" -Force

Set-Location $ProjectRoot

& $python -m pytest `
    backend/tests/test_fundamental_settings.py `
    backend/tests/test_fundamental_settings_integration.py `
    backend/tests/test_fundamental_settings_dashboard.py `
    backend/tests/test_sector_score_ranking.py `
    backend/tests/test_sector_strength_map.py `
    backend/tests/test_fundamental_report_archive_filter.py `
    backend/tests/test_fundamental_score_history.py `
    backend/tests/test_streamlit_api_compatibility.py -q
