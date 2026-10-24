$ErrorActionPreference = "Stop"

$ProjectRoot = "D:\Projects\Hisse-Robotu"

Copy-Item "$PSScriptRoot\backend\app\data\delayed_data_production_state.py" `
"$ProjectRoot\backend\app\data\" -Force

Copy-Item "$PSScriptRoot\backend\tests\test_turbo_14_8_delayed_production_state.py" `
"$ProjectRoot\backend\tests\" -Force

Set-Location $ProjectRoot
python -m pytest backend/tests/test_turbo_14_8_delayed_production_state.py -v
