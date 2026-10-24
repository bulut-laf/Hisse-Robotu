$ErrorActionPreference = "Stop"
$ProjectRoot = "D:\Projects\Hisse-Robotu"
$BackupDir = "D:\Projects\Hisse-Robotu\_fund_profile_nonblocking_autorefresh_v1\20260904-193727\backup"
Copy-Item -LiteralPath (Join-Path $BackupDir "backend\app\ui\fund_analysis_center.py") -Destination (Join-Path $ProjectRoot "backend\app\ui\fund_analysis_center.py") -Force
if (Test-Path (Join-Path $BackupDir "backend\app\funds\fund_profile_nonblocking_refresh.py")) {
    Copy-Item -LiteralPath (Join-Path $BackupDir "backend\app\funds\fund_profile_nonblocking_refresh.py") -Destination (Join-Path $ProjectRoot "backend\app\funds\fund_profile_nonblocking_refresh.py") -Force
} else {
    Remove-Item -LiteralPath (Join-Path $ProjectRoot "backend\app\funds\fund_profile_nonblocking_refresh.py") -Force -ErrorAction SilentlyContinue
}
if (Test-Path (Join-Path $BackupDir "backend\tests\test_fund_profile_nonblocking_refresh_v1.py")) {
    Copy-Item -LiteralPath (Join-Path $BackupDir "backend\tests\test_fund_profile_nonblocking_refresh_v1.py") -Destination (Join-Path $ProjectRoot "backend\tests\test_fund_profile_nonblocking_refresh_v1.py") -Force
} else {
    Remove-Item -LiteralPath (Join-Path $ProjectRoot "backend\tests\test_fund_profile_nonblocking_refresh_v1.py") -Force -ErrorAction SilentlyContinue
}
Write-Host "ROLLBACK=COMPLETE"
