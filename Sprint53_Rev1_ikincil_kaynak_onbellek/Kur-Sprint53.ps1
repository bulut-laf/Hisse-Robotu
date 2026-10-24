param(
    [string]$ProjectRoot = "D:\\Projects\\Hisse-Robotu"
)
$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if ((Resolve-Path $packageRoot).Path -ne (Resolve-Path $ProjectRoot).Path) {
    Copy-Item "$packageRoot\\backend\\*" "$ProjectRoot\\backend" -Recurse -Force
}
Set-Location $ProjectRoot
python -m pytest backend/tests/test_market_data.py backend/tests/test_batch_market_data.py backend/tests/test_market_regime_live.py backend/tests/test_data_freshness.py -q
