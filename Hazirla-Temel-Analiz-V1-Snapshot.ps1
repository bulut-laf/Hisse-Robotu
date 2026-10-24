param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"

$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$releaseRoot = Join-Path $ProjectRoot "releases"
$stageRoot = Join-Path $env:TEMP "Hisse-Robotu-Temel-Analiz-V1"
$zipPath = Join-Path $releaseRoot "Hisse-Robotu-Temel-Analiz-V1.zip"
$shaPath = Join-Path $releaseRoot "Hisse-Robotu-Temel-Analiz-V1.sha256"
$manifestPath = Join-Path $releaseRoot "RELEASE-TEMEL-ANALIZ-V1.json"

if (-not (Test-Path $python)) {
    throw "Proje sanal ortamı bulunamadı: $python"
}

Set-Location $ProjectRoot

& $python -m pytest -q
if ($LASTEXITCODE -ne 0) {
    throw "Tam regresyon başarısız. Snapshot oluşturulmadı."
}

& $python -m backend.run_system_check
if ($LASTEXITCODE -ne 0) {
    throw "Sistem kontrolü başarısız. Snapshot oluşturulmadı."
}

& $python -m compileall backend -q
if ($LASTEXITCODE -ne 0) {
    throw "Sözdizimi kontrolü başarısız. Snapshot oluşturulmadı."
}

Remove-Item $stageRoot -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $stageRoot -Force | Out-Null
New-Item -ItemType Directory -Path $releaseRoot -Force | Out-Null

$excludedDirectories = @(
    ".venv",
    ".pytest_cache",
    "__pycache__",
    "releases",
    "backups",
    "backend\data"
)

$excludedExtensions = @(
    ".pyc",
    ".pyo"
)

Get-ChildItem $ProjectRoot -Recurse -File | ForEach-Object {
    $relative = $_.FullName.Substring($ProjectRoot.Length).TrimStart("\")
    $parts = $relative -split "[\\/]"
    $skipDirectory = $false

    foreach ($excluded in $excludedDirectories) {
        if ($parts -contains $excluded -or $relative.StartsWith("$excluded\")) {
            $skipDirectory = $true
            break
        }
    }

    if ($skipDirectory) {
        return
    }

    if ($excludedExtensions -contains $_.Extension.ToLowerInvariant()) {
        return
    }

    $destination = Join-Path $stageRoot $relative
    $destinationDirectory = Split-Path -Parent $destination
    New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
    Copy-Item $_.FullName $destination -Force
}

Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
Compress-Archive -Path "$stageRoot\*" -DestinationPath $zipPath -Force

$hash = Get-FileHash -LiteralPath $zipPath -Algorithm SHA256
"$($hash.Hash)  $([System.IO.Path]::GetFileName($zipPath))" |
    Set-Content -LiteralPath $shaPath -Encoding ASCII

$manifest = [ordered]@{
    module = "Temel Analiz"
    version = "V1"
    status = "VALIDATED"
    created_at = (Get-Date).ToString("o")
    test_command = "& .\.venv\Scripts\python.exe -m pytest -q"
    baseline_before_sprint68 = 1023
    system_check = "PASSED"
    compileall = "PASSED"
    archive = [System.IO.Path]::GetFileName($zipPath)
    sha256 = $hash.Hash
    exclusions = @(
        ".venv",
        ".pytest_cache",
        "__pycache__",
        "releases",
        "backups",
        "backend\data",
        "*.pyc",
        "*.pyo"
    )
}

$manifest |
    ConvertTo-Json -Depth 5 |
    Set-Content -LiteralPath $manifestPath -Encoding UTF8

Write-Host "Snapshot: $zipPath"
Write-Host "SHA256 : $shaPath"
Write-Host "Manifest: $manifestPath"
