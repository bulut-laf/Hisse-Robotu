$ErrorActionPreference = "Stop"

$ProjectRoot = "D:\Projects\Hisse-Robotu"

Copy-Item "$PSScriptRoot\backend\app\data\delayed_status_for_adapter.py" `
"$ProjectRoot\backend\app\data\" -Force

Copy-Item "$PSScriptRoot\backend\tests\test_turbo_14_6_status_for_adapter.py" `
"$ProjectRoot\backend\tests\" -Force

Set-Location $ProjectRoot
python -m pytest backend/tests/test_turbo_14_6_status_for_adapter.py -v
