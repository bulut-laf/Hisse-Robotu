$ErrorActionPreference = "Stop"
Set-Location "D:\Projects\Hisse-Robotu"
$source = Join-Path $PSScriptRoot "backend\app\analysis\scan_top10_next_session.py"
$test = Join-Path $PSScriptRoot "backend\tests\test_scan_top10_next_session.py"
$target = ".\backend\app\analysis\scan_top10_next_session.py"
$testTarget = ".\backend\tests\test_scan_top10_next_session.py"

if (-not (Test-Path $source) -or -not (Test-Path $test)) {
    throw "Paket dosyalari eksik. ZIP'i proje kokune cikartip INSTALL_TOP10_NEXT_SESSION.ps1 dosyasini calistirin."
}
if ((Resolve-Path $source).Path -ne (Join-Path (Get-Location).Path "backend\app\analysis\scan_top10_next_session.py")) { Copy-Item $source $target -Force }
if ((Resolve-Path $test).Path -ne (Join-Path (Get-Location).Path "backend\tests\test_scan_top10_next_session.py")) { Copy-Item $test $testTarget -Force }

$runner = ".\backend\app\operations\scheduled_operation_phase_runner.py"
$content = Get-Content $runner -Raw
$importLine = "from backend.app.analysis.scan_top10_next_session import settle_scan_top10_next_session"
if ($content -notmatch [regex]::Escape($importLine)) {
    $anchor = "from backend.app.analysis.eod_candidate_performance_runtime import settle_eod_candidate_performance_history"
    if ($content.Contains($anchor)) {
        $content = $content.Replace($anchor, "$anchor`r`n$importLine")
    } else {
        throw "Runner import anchor bulunamadi; runner degistirilmedi."
    }
}
$hookMarker = "# TOP10_NEXT_SESSION_PERFORMANCE_HOOK"
if ($content -notmatch [regex]::Escape($hookMarker)) {
    $anchor = "settle_eod_candidate_performance_history(`r`n                    current_date=now.date().isoformat(),`r`n                )"
    if (-not $content.Contains($anchor)) {
        $anchor = "settle_eod_candidate_performance_history(`n                    current_date=now.date().isoformat(),`n                )"
    }
    if (-not $content.Contains($anchor)) {
        throw "Runner hook anchor bulunamadi; yeni moduller kopyalandi ancak runner entegrasyonu yapilmadi."
    }
    $insert = $anchor + "`r`n                $hookMarker`r`n                try:`r`n                    settle_scan_top10_next_session(current_date=now.date().isoformat())`r`n                except Exception:`r`n                    pass"
    $content = $content.Replace($anchor, $insert)
}
Set-Content -Path $runner -Value $content -Encoding utf8
$env:PYTHONPATH = "$PWD\backend"
.\.venv\Scripts\python.exe -m pytest backend\tests\test_scan_top10_next_session.py -q
if ($LASTEXITCODE -ne 0) { throw "Hedef testler basarisiz." }
Write-Host "TOP10_NEXT_SESSION_INSTALL=PASS"
Write-Host "Arsiv: backend\data\scan_top10_next_session_performance.json"

