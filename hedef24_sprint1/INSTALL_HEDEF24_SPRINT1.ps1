param([string]$ProjectRoot = (Get-Location).Path)
$ErrorActionPreference = "Stop"
$targetDir = Join-Path $ProjectRoot "_discovery\\erste_hungary"
$target = Join-Path $targetDir "hedef24_portfolio_seed.json"
$source = Join-Path $PSScriptRoot "data\\hedef24_portfolio_seed.json"
if (-not (Test-Path (Join-Path $ProjectRoot "backend\\dashboard.py"))) { throw "Proje kökü bulunamadı: backend\\dashboard.py yok." }
New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
if (Test-Path $target) {
  $backup = "$target.bak_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
  Copy-Item -LiteralPath $target -Destination $backup
  Write-Host "Mevcut kayıt yedeklendi: $backup"
}
Copy-Item -LiteralPath $source -Destination $target -Force
$check = Get-Content -LiteralPath $target -Raw -Encoding UTF8 | ConvertFrom-Json
if ($check.records.Count -ne 24) { throw "Doğrulama başarısız: 24 kayıt bulunamadı." }
Write-Host "Hedef 24 başlangıç verisi kuruldu: $target"
Write-Host "Kayıt sayısı: $($check.records.Count)"
Write-Host "Yalnızca JSON kuruldu; dashboard ve F1-F4 koduna dokunulmadı."
