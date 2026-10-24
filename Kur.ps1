param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== Sprint-38 KAP Settings Kurulumu ===" -ForegroundColor Cyan
Write-Host "Proje: $ProjectRoot"

if (-not (Test-Path $ProjectRoot)) {
    throw "Proje klasoru bulunamadi: $ProjectRoot"
}

$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$FilesRoot = Join-Path $PackageRoot "files"

$targets = @(
    @{
        Source = Join-Path $FilesRoot "backend\app\compliance\kap_settings.py"
        Target = Join-Path $ProjectRoot "backend\app\compliance\kap_settings.py"
    },
    @{
        Source = Join-Path $FilesRoot "backend\tests\test_kap_settings.py"
        Target = Join-Path $ProjectRoot "backend\tests\test_kap_settings.py"
    }
)

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupRoot = Join-Path $ProjectRoot "backups\Sprint-38-KapSettings-$stamp"
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null

foreach ($item in $targets) {
    if (-not (Test-Path $item.Source)) {
        throw "Paket dosyasi eksik: $($item.Source)"
    }

    $relative = $item.Target.Substring($ProjectRoot.Length).TrimStart("\")
    $backupPath = Join-Path $backupRoot $relative
    $backupDir = Split-Path -Parent $backupPath
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

    if (Test-Path $item.Target) {
        Copy-Item $item.Target $backupPath -Force
    }

    $targetDir = Split-Path -Parent $item.Target
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    Copy-Item $item.Source $item.Target -Force

    Write-Host "Yuklendi: $relative" -ForegroundColor Green
}

Write-Host ""
Write-Host "Yedek klasoru: $backupRoot" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Test calistiriliyor..." -ForegroundColor Cyan

Push-Location $ProjectRoot
try {
    $python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path $python)) {
        $python = "python"
    }

    & $python -m pytest ".\backend\tests\test_kap_settings.py" -q
    if ($LASTEXITCODE -ne 0) {
        throw "Test basarisiz oldu. Cikis kodu: $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "Kurulum ve test basarili." -ForegroundColor Green
