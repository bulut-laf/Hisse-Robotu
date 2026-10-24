$ErrorActionPreference = "Stop"

$ProjectRoot = "D:\Projects\Hisse-Robotu"

Copy-Item "$PSScriptRoot\backend\app\analysis\candidate_decision_card.py" "$ProjectRoot\backend\app\analysis\" -Force
Copy-Item "$PSScriptRoot\backend\tests\test_turbo_11_candidate_decision_card.py" "$ProjectRoot\backend\tests\" -Force

Set-Location $ProjectRoot
python -m pytest backend/tests/test_turbo_11_candidate_decision_card.py -v
