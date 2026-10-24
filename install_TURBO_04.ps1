$ErrorActionPreference = "Stop"

$ProjectRoot = "D:\Projects\Hisse-Robotu"

Copy-Item "$PSScriptRoot\backend\app\analysis\morning_action_board.py" "$ProjectRoot\backend\app\analysis\" -Force
Copy-Item "$PSScriptRoot\backend\tests\test_turbo_04_action_board.py" "$ProjectRoot\backend\tests\" -Force

Set-Location $ProjectRoot
python -m pytest backend/tests/test_turbo_04_action_board.py -v
