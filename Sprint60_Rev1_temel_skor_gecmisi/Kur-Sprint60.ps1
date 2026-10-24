param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Copy-Item `
    "$packageRoot\backend\app\data\fundamental_score_store.py" `
    "$ProjectRoot\backend\app\data\fundamental_score_store.py" `
    -Force

Copy-Item `
    "$packageRoot\backend\app\analysis\fundamental_score_history.py" `
    "$ProjectRoot\backend\app\analysis\fundamental_score_history.py" `
    -Force

Copy-Item `
    "$packageRoot\backend\dashboard.py" `
    "$ProjectRoot\backend\dashboard.py" `
    -Force

Copy-Item `
    "$packageRoot\backend\tests\test_fundamental_score_history_store.py" `
    "$ProjectRoot\backend\tests\test_fundamental_score_history_store.py" `
    -Force

Copy-Item `
    "$packageRoot\backend\tests\test_fundamental_score_history.py" `
    "$ProjectRoot\backend\tests\test_fundamental_score_history.py" `
    -Force

Copy-Item `
    "$packageRoot\backend\tests\test_fundamental_score_history_dashboard.py" `
    "$ProjectRoot\backend\tests\test_fundamental_score_history_dashboard.py" `
    -Force

Set-Location $ProjectRoot

python -m pytest `
    backend/tests/test_fundamental_score_history_store.py `
    backend/tests/test_fundamental_score_history.py `
    backend/tests/test_fundamental_score_history_dashboard.py `
    backend/tests/test_fundamental_score_store.py `
    backend/tests/test_fundamental_score_store_dashboard.py `
    backend/tests/test_fundamental_quality.py `
    backend/tests/test_fundamental_dashboard.py `
    backend/tests/test_streamlit_api_compatibility.py -q
