$ErrorActionPreference = "Stop"

$ProjectRoot = "D:\Projects\Hisse-Robotu"

$src = "$PSScriptRoot\backend\app\analysis\morning_data_status_adapter.py"
$dst = "$ProjectRoot\backend\app\analysis\morning_data_status_adapter.py"

if ($src -ne $dst) {
    Copy-Item $src $dst -Force
}

$src = "$PSScriptRoot\backend\tests\test_turbo_14_4_morning_data_status_adapter.py"
$dst = "$ProjectRoot\backend\tests\test_turbo_14_4_morning_data_status_adapter.py"

if ($src -ne $dst) {
    Copy-Item $src $dst -Force
}

Set-Location $ProjectRoot
python -m pytest backend/tests/test_turbo_14_4_morning_data_status_adapter.py -v
