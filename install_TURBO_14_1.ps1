$ProjectRoot = "D:\Projects\Hisse-Robotu"
Copy-Item "$PSScriptRoot\backend\app\operations\valid_data_state.py" "$ProjectRoot\backend\app\operations\" -Force
Copy-Item "$PSScriptRoot\backend\tests\test_turbo_14_1_valid_data_state.py" "$ProjectRoot\backend\tests\" -Force
Set-Location $ProjectRoot
python -m pytest backend/tests/test_turbo_14_1_valid_data_state.py -v
