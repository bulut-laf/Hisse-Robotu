$ErrorActionPreference = "Stop"
Set-Location "D:\Projects\Hisse-Robotu"
$packageRoot = (Split-Path -Parent $MyInvocation.MyCommand.Path)
$files = @(
  @{ Source = (Join-Path $packageRoot "backend\app\analysis\scan_top10_next_session_v2.py"); Target = ".\backend\app\analysis\scan_top10_next_session_v2.py" },
  @{ Source = (Join-Path $packageRoot "backend\tests\test_scan_top10_next_session_v2.py"); Target = ".\backend\tests\test_scan_top10_next_session_v2.py" }
)
foreach ($file in $files) {
  if (-not (Test-Path $file.Source)) { throw "Paket dosyasi eksik: $($file.Source)" }
  $sourceFull = [System.IO.Path]::GetFullPath($file.Source)
  $targetFull = [System.IO.Path]::GetFullPath($file.Target)
  if ($sourceFull -ne $targetFull) { Copy-Item $sourceFull $targetFull -Force }
}
$env:PYTHONPATH = "$PWD"
.\.venv\Scripts\python.exe -m pytest .\backend\tests\test_scan_top10_next_session_v2.py -q
if ($LASTEXITCODE -ne 0) { throw "V2 hedef testleri basarisiz; runner entegrasyonu yapilmadi." }
Write-Host "TOP10_NEXT_SESSION_V2_TARGET_TESTS=PASS"
Write-Host "V2 arsiv: backend\data\scan_top10_next_session_performance_v2.json"
Write-Host "Mevcut AL-SAT ve V1 modulu degistirilmedi. Runner entegrasyonu hedef testler sonrasi ayri adimdir."

