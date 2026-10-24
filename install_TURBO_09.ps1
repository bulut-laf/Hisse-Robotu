$ErrorActionPreference = "Stop"

$ProjectRoot = "D:\Projects\Hisse-Robotu"

Copy-Item "$PSScriptRoot\backend\app\analysis\v1_release_candidate_gate.py" "$ProjectRoot\backend\app\analysis\" -Force
Copy-Item "$PSScriptRoot\backend\tests\test_turbo_09_release_candidate_gate.py" "$ProjectRoot\backend\tests\" -Force

Set-Location $ProjectRoot
python -m pytest backend/tests/test_turbo_09_release_candidate_gate.py -v
