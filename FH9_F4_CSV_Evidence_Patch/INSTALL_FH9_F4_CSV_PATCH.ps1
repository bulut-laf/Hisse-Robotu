param([string]$ProjectRoot = "D:\Projects\Hisse-Robotu")
$ErrorActionPreference = "Stop"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$source = Join-Path $PSScriptRoot "src"
$parserSource = Join-Path $source "erste_hungary_f4_csv.py"
$testsSource = Join-Path $source "test_erste_hungary_f4_csv.py"
$runnerSource = Join-Path $source "run_erste_hungary_f4_csv.py"
$intl = Join-Path $ProjectRoot "backend\app\funds\international"
$tests = Join-Path $ProjectRoot "backend\tests"
$disc = Join-Path $ProjectRoot "_discovery\erste_hungary"
New-Item -ItemType Directory -Force -Path $intl,$tests,$disc | Out-Null
Copy-Item $parserSource (Join-Path $intl "erste_hungary_f4_csv.py") -Force
Copy-Item $testsSource (Join-Path $tests "test_erste_hungary_f4_csv.py") -Force
Copy-Item $runnerSource (Join-Path $disc "run_erste_hungary_f4_csv.py") -Force
$py = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $cmd = Get-Command python.exe -ErrorAction SilentlyContinue; if ($cmd) {$py=$cmd.Source} else { throw "PYTHON_NOT_FOUND" } }
$env:PYTHONPATH = $ProjectRoot
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
Push-Location $ProjectRoot
try {
  Write-Host "=== FH9 F4 CSV PARSER TARGET TESTS ==="
  & $py -m pytest backend\tests\test_erste_hungary_f4_csv.py -q
  if ($LASTEXITCODE -ne 0) { throw "F4_CSV_TARGET_TESTS_FAILED:$LASTEXITCODE" }
  Write-Host "TARGET_TESTS=PASS"
  Write-Host "=== DOWNLOAD AND PARSE 7 TARGET FUNDS (NO HTML SCAN) ==="
  & $py _discovery\erste_hungary\run_erste_hungary_f4_csv.py
  if ($LASTEXITCODE -ne 0) { throw "F4_CSV_RUNNER_FAILED:$LASTEXITCODE" }
  Write-Host "CSV_RUNNER=PASS"
  Write-Host "NOTE: This package does not alter the existing production F4 bridge."
  Write-Host "NOTE: Full regression is intentionally not claimed; review evidence summary first."
}
finally { Pop-Location }
