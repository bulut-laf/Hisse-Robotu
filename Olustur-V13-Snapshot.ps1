param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$releaseDir = Join-Path $ProjectRoot "releases"
$zipPath = Join-Path $releaseDir "Hisse-Robotu-V1.3.zip"
$shaPath = Join-Path $releaseDir "Hisse-Robotu-V1.3.sha256"
$manifestPath = Join-Path $releaseDir "RELEASE-V1.3.json"
$tempRoot = Join-Path $env:TEMP "Hisse-Robotu-V1.3-Snapshot"

if (-not (Test-Path $python)) {
    throw "Proje sanal ortamı bulunamadı: $python"
}

Set-Location $ProjectRoot

Write-Host "1/3 Tam regresyon çalıştırılıyor..."
& $python -m pytest -q
if ($LASTEXITCODE -ne 0) {
    throw "Tam regresyon başarısız. Snapshot oluşturulmadı."
}

Write-Host "2/3 Sistem kontrolü çalıştırılıyor..."
& $python -c "from backend.app.diagnostics.system_check import sistem_kontrolu_calistir; r=sistem_kontrolu_calistir(); print(r.json_metni()); raise SystemExit(0 if r.kullanima_hazir else 1)"
if ($LASTEXITCODE -ne 0) {
    throw "Sistem kontrolü başarısız. Snapshot oluşturulmadı."
}

Write-Host "3/3 Snapshot hazırlanıyor..."
Remove-Item $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null

Copy-Item "$ProjectRoot\backend" "$tempRoot\backend" -Recurse -Force
Copy-Item "$ProjectRoot\PROJECT_NOTES.md" "$tempRoot\PROJECT_NOTES.md" -Force
Copy-Item "$ProjectRoot\KULLANIM_KILAVUZU.md" "$tempRoot\KULLANIM_KILAVUZU.md" -Force
Copy-Item "$ProjectRoot\requirements.txt" "$tempRoot\requirements.txt" -Force -ErrorAction SilentlyContinue
Copy-Item "$ProjectRoot\Hisse-Robotu-Baslat.ps1" "$tempRoot\Hisse-Robotu-Baslat.ps1" -Force -ErrorAction SilentlyContinue

Get-ChildItem $tempRoot -Recurse -Directory -Filter "__pycache__" |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem $tempRoot -Recurse -File -Include "*.pyc","*.bak" |
    Remove-Item -Force -ErrorAction SilentlyContinue

Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
Compress-Archive -Path "$tempRoot\*" -DestinationPath $zipPath -Force

$hash = (Get-FileHash $zipPath -Algorithm SHA256).Hash
[System.IO.File]::WriteAllText(
    $shaPath,
    "$hash  Hisse-Robotu-V1.3.zip`n",
    [System.Text.UTF8Encoding]::new($false)
)

$fileCount = (Get-ChildItem $tempRoot -Recurse -File).Count
$manifest = [ordered]@{
    version = "V1.3"
    created_at = (Get-Date).ToString("o")
    regression_baseline_before_sprint81 = 1176
    snapshot_file = "Hisse-Robotu-V1.3.zip"
    sha256 = $hash
    file_count = $fileCount
    scope = @(
        "Sprint-75 Gecikmeli Veri Pilotu",
        "Sprint-76 Günlük Operasyon Paneli",
        "Sprint-77 Otomatik Sinyal Kaydı",
        "Sprint-78 Gölge Portföy",
        "Sprint-79 Haftalık Performans Raporu",
        "Sprint-80 Başarı Karşılaştırması",
        "Sprint-81 Kalibrasyon Kararı ve Snapshot"
    )
}
$manifestJson = $manifest | ConvertTo-Json -Depth 5
[System.IO.File]::WriteAllText(
    $manifestPath,
    $manifestJson,
    [System.Text.UTF8Encoding]::new($false)
)

Get-Item $zipPath, $shaPath, $manifestPath |
    Select-Object FullName, Length, LastWriteTime
