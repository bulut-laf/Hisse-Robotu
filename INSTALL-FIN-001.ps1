$ErrorActionPreference = "Stop"
$Repo = "D:\Projects\Hisse-Robotu"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not (Test-Path $Repo)) { throw "HISSE ROBOTU REPO NOT FOUND: $Repo" }

$targets = @(
  @{ Src = "backend\app\models\financial_intelligence_models.py"; Dst = "backend\app\models\financial_intelligence_models.py" },
  @{ Src = "backend\app\data\kap_financial_xls.py"; Dst = "backend\app\data\kap_financial_xls.py" },
  @{ Src = "backend\tests\test_fin001_kap_financial_xls.py"; Dst = "backend\tests\test_fin001_kap_financial_xls.py" }
)

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backup = Join-Path $Repo "_backup\FIN001_$stamp"
New-Item -ItemType Directory -Path $backup -Force | Out-Null

foreach ($item in $targets) {
  $src = Join-Path $Here $item.Src
  $dst = Join-Path $Repo $item.Dst
  if (-not (Test-Path $src)) { throw "PACKAGE FILE MISSING: $src" }
  if (Test-Path $dst) {
    $rel = $item.Dst
    $bak = Join-Path $backup $rel
    New-Item -ItemType Directory -Path (Split-Path -Parent $bak) -Force | Out-Null
    Copy-Item $dst $bak -Force
  }
  New-Item -ItemType Directory -Path (Split-Path -Parent $dst) -Force | Out-Null
  Copy-Item $src $dst -Force
}

Push-Location $Repo
try {
  & ".\.venv\Scripts\python.exe" -m pytest backend\tests\test_fin001_kap_financial_xls.py -q
  if ($LASTEXITCODE -ne 0) { throw "FIN-001 TARGET TEST FAILED" }
  & ".\.venv\Scripts\python.exe" -m compileall backend -q
  if ($LASTEXITCODE -ne 0) { throw "FIN-001 COMPILEALL FAILED" }
  Write-Host "FIN-001 INSTALL PASS"
  Write-Host "BACKUP=$backup"
} catch {
  Write-Host "FIN-001 FAILED - ROLLBACK"
  foreach ($item in $targets) {
    $dst = Join-Path $Repo $item.Dst
    $bak = Join-Path $backup $item.Dst
    if (Test-Path $bak) { Copy-Item $bak $dst -Force }
    elseif (Test-Path $dst) { Remove-Item $dst -Force }
  }
  throw
} finally {
  Pop-Location
}
