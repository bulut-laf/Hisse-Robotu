param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Copy-Item "$packageRoot\backend\dashboard.py" `
    "$ProjectRoot\backend\dashboard.py" -Force

Set-Location $ProjectRoot

python -m pytest `
    backend/tests/test_fundamental_models.py `
    backend/tests/test_fundamental_analysis.py `
    backend/tests/test_fundamental_data.py `
    backend/tests/test_fundamental_dashboard.py `
    backend/tests/test_streamlit_api_compatibility.py -q
