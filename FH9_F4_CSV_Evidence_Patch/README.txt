FH9 / F4 CSV evidence patch

Contents:
- src/erste_hungary_f4_csv.py: ISO-8859-2-aware parser that locates the actual daily-table header after metadata rows.
- src/test_erste_hungary_f4_csv.py: deterministic parser and metric contract tests.
- src/run_erste_hungary_f4_csv.py: downloads and archives the seven target CSV responses, parses them, and writes per-fund JSON plus summary.json.
- INSTALL_FH9_F4_CSV_PATCH.ps1: copies files into D:\Projects\Hisse-Robotu, runs target tests, then downloads/parses the seven funds.

Safety / scope:
- This patch does NOT overwrite or mutate the existing production F4 bridge or trading logic.
- net_flow_ratio remains null unless official net investor flow is supplied to the explicit function; daily turnover is not used as a proxy.
- Fund size change is the percent change between the latest two valid daily NAV observations, not proof of investor inflow.
- automatic_trade_authority and trade_authority remain NONE; forced_fill remains false.
- Full regression is not run automatically because this patch first needs review of the real CSV evidence and production bridge integration.

Run from PowerShell:
  Expand-Archive -Path .\FH9_F4_CSV_Evidence_Patch.zip -DestinationPath .\FH9_F4_CSV_Evidence_Patch -Force
  Set-ExecutionPolicy -Scope Process Bypass
  .\FH9_F4_CSV_Evidence_Patch\INSTALL_FH9_F4_CSV_PATCH.ps1
