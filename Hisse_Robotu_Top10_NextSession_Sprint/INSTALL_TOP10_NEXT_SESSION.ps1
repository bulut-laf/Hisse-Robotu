$ErrorActionPreference = "Stop"
Set-Location "D:\Projects\Hisse-Robotu"
$source = Join-Path $PSScriptRoot "backend\app\analysis\scan_top10_next_session.py"
$test = Join-Path $PSScriptRoot "backend\tests\test_scan_top10_next_session.py"
if (!(Test-Path $source) -or !(Test-Path $test)) { throw "Paket dosyalari eksik. ZIP'i acip bu scripti paket klasorunden calistirin." }
Copy-Item $source ".\backend\app\analysis\scan_top10_next_session.py" -Force
Copy-Item $test ".\backend\tests\test_scan_top10_next_session.py" -Force
$runner = ".\backend\app\operations\scheduled_operation_phase_runner.py"
$content = Get-Content $runner -Raw
$settleImport = "from backend.app.analysis.scan_top10_next_session import settle_scan_top10_next_session"
$recordImport = "from backend.app.analysis.scan_top10_next_session import record_scan_top10_snapshot"
if ($content -notmatch [regex]::Escape($settleImport)) { throw "Top10 settle import bulunamadi; runner degistirilmedi." }
if ($content -notmatch [regex]::Escape($recordImport)) {
  $content = $content.Replace($settleImport, "from backend.app.analysis.scan_top10_next_session import settle_scan_top10_next_session, record_scan_top10_snapshot")
}
# Capture the return value of the existing scan; keep scan parameters and AL-SAT path unchanged.
$pattern = '(?s)MomentumDiscoveryService\(\)\.calistir\(\s*MomentumDiscoveryRequest\(\s*evren=TARAMA_EVRENLERI\[4\],\s*maksimum_aday=25,\s*minimum_skor=55,\s*internetten_evren_guncelle=False,\s*\)\s*\)'
if ($content -notmatch 'momentum_result\s*=\s*MomentumDiscoveryService\(\)\.calistir') {
  $content2 = [regex]::Replace($content, $pattern, { param($m) 'momentum_result = ' + $m.Value }, 1)
  if ($content2 -eq $content) { throw "Momentum tarama blogu bulunamadi; runner degistirilmedi." }
  $content = $content2
}
if ($content -notmatch 'record_scan_top10_snapshot\(run_date=now\.date\(\)\.isoformat\(\),\s*candidates=momentum_result\.adaylar') {
  $anchor = '(?s)(momentum_result\s*=\s*MomentumDiscoveryService\(\)\.calistir\(.*?\)\s*\)\s*except Exception:\s*pass)'
  $replacement = '$1' + "`r`n        try:`r`n            record_scan_top10_snapshot(run_date=now.date().isoformat(), candidates=momentum_result.adaylar)`r`n        except Exception:`r`n            pass"
  $content2 = [regex]::Replace($content, $anchor, $replacement, 1)
  if ($content2 -eq $content) { throw "Momentum snapshot hook eklenemedi; runner degistirilmedi." }
  $content = $content2
}
Set-Content -Path $runner -Value $content -Encoding utf8
$env:PYTHONPATH = "$PWD"
.\.venv\Scripts\python.exe -m pytest backend\tests\test_scan_top10_next_session.py -q
if ($LASTEXITCODE -ne 0) { throw "Top10 hedef testleri basarisiz." }
Write-Host "TOP10_NEXT_SESSION_SNAPSHOT_PATCH=PASS"
Write-Host "Gercek adaylar: MomentumDiscoveryService().calistir(...).adaylar"
Write-Host "Arsiv: backend\data\scan_top10_next_session_performance.json"
