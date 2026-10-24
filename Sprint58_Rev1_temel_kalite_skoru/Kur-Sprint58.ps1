param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Copy-Item "$packageRoot\backend\app\analysis\fundamental_quality.py" `
    "$ProjectRoot\backend\app\analysis\fundamental_quality.py" -Force
Copy-Item "$packageRoot\backend\dashboard.py" `
    "$ProjectRoot\backend\dashboard.py" -Force
Copy-Item "$packageRoot\backend\tests\test_fundamental_quality.py" `
    "$ProjectRoot\backend\tests\test_fundamental_quality.py" -Force
Copy-Item "$packageRoot\backend\tests\test_fundamental_quality_dashboard.py" `
    "$ProjectRoot\backend\tests\test_fundamental_quality_dashboard.py" -Force

Set-Location $ProjectRoot

python -m pytest `
    backend/tests/test_fundamental_quality.py `
    backend/tests/test_fundamental_quality_dashboard.py `
    backend/tests/test_fundamental_analysis.py `
    backend/tests/test_fundamental_data.py `
    backend/tests/test_fundamental_dashboard.py `
    backend/tests/test_streamlit_api_compatibility.py -q
