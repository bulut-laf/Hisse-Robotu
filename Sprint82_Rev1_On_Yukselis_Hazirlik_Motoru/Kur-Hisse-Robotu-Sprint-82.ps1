param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Python sanal ortamı bulunamadı: $Python"
}

$TargetModule = Join-Path $ProjectRoot "backend\app\prebreakout"
New-Item -ItemType Directory -Path $TargetModule -Force | Out-Null

Copy-Item "$PackageRoot\backend\app\prebreakout\*" $TargetModule -Recurse -Force

$TestFiles = @(
    "prebreakout_test_helpers.py",
    "test_prebreakout_models.py",
    "test_prebreakout_features.py",
    "test_prebreakout_filters.py",
    "test_prebreakout_score.py",
    "test_prebreakout_stage.py",
    "test_prebreakout_engine.py"
)

foreach ($TestFile in $TestFiles) {
    Copy-Item `
        (Join-Path $PackageRoot "backend\tests\$TestFile") `
        (Join-Path $ProjectRoot "backend\tests\$TestFile") `
        -Force
}

Set-Location $ProjectRoot

& $Python -m pytest `
    backend/tests/test_prebreakout_models.py `
    backend/tests/test_prebreakout_features.py `
    backend/tests/test_prebreakout_filters.py `
    backend/tests/test_prebreakout_score.py `
    backend/tests/test_prebreakout_stage.py `
    backend/tests/test_prebreakout_engine.py `
    -q

if ($LASTEXITCODE -ne 0) {
    throw "Sprint-82 hedef testleri başarısız."
}

Write-Host ""
Write-Host "Sprint-82 kuruldu ve hedef testleri tamamlandı."
Write-Host "Sonraki adım: tam regresyon için"
Write-Host '& ".\.venv\Scripts\python.exe" -m pytest -q'
