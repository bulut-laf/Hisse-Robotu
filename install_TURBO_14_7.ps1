$ErrorActionPreference = "Stop"

$ProjectRoot = "D:\Projects\Hisse-Robotu"

Copy-Item "$PSScriptRoot\backend\app\data\status_for_production_adapter.py" `
"$ProjectRoot\backend\app\data\" -Force

Copy-Item "$PSScriptRoot\backend\tests\test_turbo_14_7_status_for_production.py" `
"$ProjectRoot\backend\tests\" -Force

Set-Location $ProjectRoot
python -m pytest backend/tests/test_turbo_14_7_status_for_production.py -v
