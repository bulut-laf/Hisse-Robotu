param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Copy-Item "$packageRoot\backend\app\data\data_source_recovery.py" `
    "$ProjectRoot\backend\app\data\data_source_recovery.py" -Force
Copy-Item "$packageRoot\backend\app\analysis\market_regime.py" `
    "$ProjectRoot\backend\app\analysis\market_regime.py" -Force

Set-Location $ProjectRoot
python -m pytest backend/tests/test_market_data.py backend/tests/test_batch_market_data.py backend/tests/test_market_regime_live.py backend/tests/test_data_freshness.py -q
