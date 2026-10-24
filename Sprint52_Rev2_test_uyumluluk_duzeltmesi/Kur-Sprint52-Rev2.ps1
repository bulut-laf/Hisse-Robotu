param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$source = Join-Path $packageRoot "backend\app\analysis\market_regime.py"
$target = Join-Path $ProjectRoot "backend\app\analysis\market_regime.py"

Copy-Item $source $target -Force
Set-Location $ProjectRoot

python -m pytest backend/tests/test_data_freshness.py backend/tests/test_market_regime_live.py backend/tests/test_momentum_freshness_regime_merge.py backend/tests/test_market_regime_dashboard.py -q
