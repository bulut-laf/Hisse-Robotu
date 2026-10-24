$ErrorActionPreference = "Stop"

$ProjectRoot = "D:\Projects\Hisse-Robotu"

Copy-Item "$PSScriptRoot\backend\app\data\delayed_data_status_bridge.py" `
"$ProjectRoot\backend\app\data\" -Force

Copy-Item "$PSScriptRoot\backend\tests\test_turbo_14_5_rev1_delayed_data_integration.py" `
"$ProjectRoot\backend\tests\" -Force

Set-Location $ProjectRoot
python -m pytest backend/tests/test_turbo_14_5_rev1_delayed_data_integration.py -v
