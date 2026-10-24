$ErrorActionPreference = "Stop"

$ProjectRoot = "D:\Projects\Hisse-Robotu"

Copy-Item "$PSScriptRoot\backend\app\data\valid_daily_data_state.py" `
"$ProjectRoot\backend\app\data\" -Force

Copy-Item "$PSScriptRoot\backend\tests\test_turbo_14_2_daily_data_state.py" `
"$ProjectRoot\backend\tests\" -Force

Set-Location $ProjectRoot

python -m pytest backend/tests/test_turbo_14_2_daily_data_state.py -v
