$ErrorActionPreference = "Stop"

$ProjectRoot = "D:\Projects\Hisse-Robotu"

Copy-Item "$PSScriptRoot\backend\app\analysis\daily_operation_data_bridge.py" `
"$ProjectRoot\backend\app\analysis\" -Force

Copy-Item "$PSScriptRoot\backend\tests\test_turbo_14_3_operation_data_bridge.py" `
"$ProjectRoot\backend\tests\" -Force

Set-Location $ProjectRoot

python -m pytest backend/tests/test_turbo_14_3_operation_data_bridge.py -v
