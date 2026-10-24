$ErrorActionPreference = 'Stop'
$started = Get-Date
'SMOKE_TEST_STARTED=' + $started.ToString('o') | Set-Content -LiteralPath 'D:\Projects\Hisse-Robotu\backend\logs\scheduled-task-diagnostics\scheduler-smoke-test.log' -Encoding UTF8
'SMOKE_TEST_FINISHED=' + (Get-Date).ToString('o') | Add-Content -LiteralPath 'D:\Projects\Hisse-Robotu\backend\logs\scheduled-task-diagnostics\scheduler-smoke-test.log' -Encoding UTF8
exit 0
