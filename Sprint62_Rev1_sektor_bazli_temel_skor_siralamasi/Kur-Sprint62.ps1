param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Proje sanal ortamı bulunamadı: $python"
}

Copy-Item `
    "$packageRoot\backend\app\analysis\sector_score_ranking.py" `
    "$ProjectRoot\backend\app\analysis\sector_score_ranking.py" `
    -Force

Copy-Item `
    "$packageRoot\backend\dashboard.py" `
    "$ProjectRoot\backend\dashboard.py" `
    -Force

Copy-Item `
    "$packageRoot\backend\tests\test_sector_score_ranking.py" `
    "$ProjectRoot\backend\tests\test_sector_score_ranking.py" `
    -Force

Copy-Item `
    "$packageRoot\backend\tests\test_sector_score_ranking_dashboard.py" `
    "$ProjectRoot\backend\tests\test_sector_score_ranking_dashboard.py" `
    -Force

Set-Location $ProjectRoot

& $python -m pytest `
    backend/tests/test_sector_score_ranking.py `
    backend/tests/test_sector_score_ranking_dashboard.py `
    backend/tests/test_sector_reference.py `
    backend/tests/test_sector_reference_dashboard.py `
    backend/tests/test_fundamental_score_store.py `
    backend/tests/test_fundamental_score_history.py `
    backend/tests/test_fundamental_score_history_dashboard.py `
    backend/tests/test_streamlit_api_compatibility.py -q
