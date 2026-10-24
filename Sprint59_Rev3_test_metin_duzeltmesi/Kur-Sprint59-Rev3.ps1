param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Copy-Item `
    "$packageRoot\backend\tests\test_fundamental_score_store_dashboard.py" `
    "$ProjectRoot\backend\tests\test_fundamental_score_store_dashboard.py" `
    -Force

Set-Location $ProjectRoot

python -m pytest `
    backend/tests/test_fundamental_score_store.py `
    backend/tests/test_fundamental_score_store_dashboard.py `
    backend/tests/test_fundamental_quality.py `
    backend/tests/test_fundamental_quality_dashboard.py `
    backend/tests/test_fundamental_dashboard.py `
    backend/tests/test_streamlit_api_compatibility.py -q
