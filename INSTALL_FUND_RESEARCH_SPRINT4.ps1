param([string]$ProjectRoot = "D:\Projects\Hisse-Robotu")
$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) { throw "Project root not found: $ProjectRoot" }
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupRoot = Join-Path $ProjectRoot "_backups\fund_research_sprint4_$stamp"
$relativeFiles = @(
 "backend\app\funds\portfolio.py",
 "backend\tests\test_fund_research_sprint4.py",
 "PROJECT_NOTES_FUND_RESEARCH_SPRINT4.md"
)
foreach ($relative in $relativeFiles) {
 $source = Join-Path $packageRoot $relative; $destination = Join-Path $ProjectRoot $relative
 if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Package file missing: $source" }
 if (Test-Path -LiteralPath $destination) {
  $backup = Join-Path $backupRoot $relative
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $backup) | Out-Null
  Copy-Item -LiteralPath $destination -Destination $backup -Force
  Write-Host "BACKUP: $destination -> $backup"
 }
 New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
 Copy-Item -LiteralPath $source -Destination $destination -Force
 Write-Host "INSTALLED: $destination"
}
Push-Location $ProjectRoot
try {
 $python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
 if (-not (Test-Path $python)) { $python = "python" }
 & $python -m pytest backend\tests\test_fund_research_sprint4.py -q
 if ($LASTEXITCODE -ne 0) { throw "Sprint 4 target tests failed with exit code $LASTEXITCODE" }
 Write-Host "TARGET_TESTS=PASS"
 Write-Host "NEXT: Run full regression: .\.venv\Scripts\python.exe -m pytest"
} finally { Pop-Location }
