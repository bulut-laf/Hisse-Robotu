$ErrorActionPreference = "Stop"
Copy-Item -LiteralPath "D:\Projects\Hisse-Robotu\_tefas_universe_nonblocking_final_v1\20260904-201218\backup\backend\dashboard.py" -Destination "D:\Projects\Hisse-Robotu\backend\dashboard.py" -Force
if (Test-Path "D:\Projects\Hisse-Robotu\_tefas_universe_nonblocking_final_v1\20260904-201218\backup\backend\app\funds\tefas_universe_nonblocking_refresh.py") {
    Copy-Item -LiteralPath "D:\Projects\Hisse-Robotu\_tefas_universe_nonblocking_final_v1\20260904-201218\backup\backend\app\funds\tefas_universe_nonblocking_refresh.py" -Destination "D:\Projects\Hisse-Robotu\backend\app\funds\tefas_universe_nonblocking_refresh.py" -Force
} else {
    Remove-Item -LiteralPath "D:\Projects\Hisse-Robotu\backend\app\funds\tefas_universe_nonblocking_refresh.py" -Force -ErrorAction SilentlyContinue
}
if (Test-Path "D:\Projects\Hisse-Robotu\_tefas_universe_nonblocking_final_v1\20260904-201218\backup\backend\tests\test_tefas_universe_nonblocking_refresh_v1.py") {
    Copy-Item -LiteralPath "D:\Projects\Hisse-Robotu\_tefas_universe_nonblocking_final_v1\20260904-201218\backup\backend\tests\test_tefas_universe_nonblocking_refresh_v1.py" -Destination "D:\Projects\Hisse-Robotu\backend\tests\test_tefas_universe_nonblocking_refresh_v1.py" -Force
} else {
    Remove-Item -LiteralPath "D:\Projects\Hisse-Robotu\backend\tests\test_tefas_universe_nonblocking_refresh_v1.py" -Force -ErrorAction SilentlyContinue
}
Write-Host "ROLLBACK=COMPLETE"
