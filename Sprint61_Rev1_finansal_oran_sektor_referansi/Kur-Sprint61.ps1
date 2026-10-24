param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Copy-Item `
    "$packageRoot\backend\app\analysis\sector_reference.py" `
    "$ProjectRoot\backend\app\analysis\sector_reference.py" `
    -Force

Copy-Item `
    "$packageRoot\backend\dashboard.py" `
    "$ProjectRoot\backend\dashboard.py" `
    -Force

Copy-Item `
    "$packageRoot\backend\tests\test_sector_reference.py" `
    "$ProjectRoot\backend\tests\test_sector_reference.py" `
    -Force

Copy-Item `
    "$packageRoot\backend\tests\test_sector_reference_dashboard.py" `
    "$ProjectRoot\backend\tests\test_sector_reference_dashboard.py" `
    -Force

Copy-Item `
    "$packageRoot\backend\data\sector_reference_sample.csv" `
    "$ProjectRoot\backend\data\sector_reference_sample.csv" `
    -Force

Set-Location $ProjectRoot

python -m pytest `
    backend/tests/test_sector_reference.py `
    backend/tests/test_sector_reference_dashboard.py `
    backend/tests/test_fundamental_analysis.py `
    backend/tests/test_fundamental_dashboard.py `
    backend/tests/test_fundamental_score_history.py `
    backend/tests/test_fundamental_score_history_dashboard.py `
    backend/tests/test_streamlit_api_compatibility.py -q
