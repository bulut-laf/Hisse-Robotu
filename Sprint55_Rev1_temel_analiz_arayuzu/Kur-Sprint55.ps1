param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Copy-Item "$packageRoot\backend\dashboard.py" `
    "$ProjectRoot\backend\dashboard.py" -Force

Copy-Item "$packageRoot\backend\tests\test_fundamental_dashboard.py" `
    "$ProjectRoot\backend\tests\test_fundamental_dashboard.py" -Force

Set-Location $ProjectRoot

python -m pytest `
    backend/tests/test_fundamental_models.py `
    backend/tests/test_fundamental_analysis.py `
    backend/tests/test_fundamental_data.py `
    backend/tests/test_fundamental_dashboard.py -q
