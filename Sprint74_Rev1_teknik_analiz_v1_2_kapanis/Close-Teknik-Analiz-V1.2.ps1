param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"

$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$releaseDir = Join-Path $ProjectRoot "releases"
$releaseName = "Hisse-Robotu-Teknik-Analiz-V1.2"
$snapshot = Join-Path $releaseDir "$releaseName.zip"
$shaFile = Join-Path $releaseDir "$releaseName.sha256"
$releaseJson = Join-Path $releaseDir "RELEASE-TEKNIK-ANALIZ-V1.2.json"
$staging = Join-Path $env:TEMP "$releaseName-staging"

if (-not (Test-Path $python)) {
    throw "Proje sanal ortamı bulunamadı: $python"
}

Set-Location $ProjectRoot

Write-Host "`n[1/5] Teknik Analiz V1.2 hedef testleri"
$targetTests = @(
    "backend/tests/test_divergence_analysis.py",
    "backend/tests/test_divergence_analysis_dashboard.py",
    "backend/tests/test_technical_decision_matrix.py",
    "backend/tests/test_technical_decision_matrix_dashboard.py",
    "backend/tests/test_signal_outcome_tracking.py",
    "backend/tests/test_signal_outcome_tracking_dashboard.py",
    "backend/tests/test_indicator_contribution.py",
    "backend/tests/test_indicator_contribution_dashboard.py",
    "backend/tests/test_walk_forward_calibration.py",
    "backend/tests/test_walk_forward_calibration_dashboard.py",
    "backend/tests/test_technical_analysis_v12_closeout.py",
    "backend/tests/test_streamlit_api_compatibility.py"
)

$targetOutput = & $python -m pytest @targetTests -q 2>&1
$targetExit = $LASTEXITCODE
$targetOutput | ForEach-Object { Write-Host $_ }
if ($targetExit -ne 0) {
    throw "Hedef testler başarısız. Snapshot oluşturulmadı."
}

Write-Host "`n[2/5] Tam regresyon"
$regressionOutput = & $python -m pytest -q 2>&1
$regressionExit = $LASTEXITCODE
$regressionOutput | ForEach-Object { Write-Host $_ }
if ($regressionExit -ne 0) {
    throw "Tam regresyon başarısız. Snapshot oluşturulmadı."
}

Write-Host "`n[3/5] Sistem kontrolü"
$systemOutput = & $python -m backend.run_system_check 2>&1
$systemExit = $LASTEXITCODE
$systemOutput | ForEach-Object { Write-Host $_ }
if ($systemExit -ne 0) {
    throw "Sistem kontrolü başarısız. Snapshot oluşturulmadı."
}
$systemText = $systemOutput -join "`n"
if (
    $systemText -notmatch "Sistem kullanıma hazır" -and
    $systemText -notmatch "Sistem kullanıma haz.r"
) {
    throw "Sistem kontrolü kullanıma hazır sonucu vermedi. Snapshot oluşturulmadı."
}

Write-Host "`n[4/5] Python sözdizimi"
& $python -m compileall backend -q
if ($LASTEXITCODE -ne 0) {
    throw "Python sözdizimi kontrolü başarısız. Snapshot oluşturulmadı."
}

Write-Host "`n[5/5] Temiz snapshot, SHA-256 ve release kaydı"
New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null
Remove-Item $staging -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $snapshot, $shaFile, $releaseJson -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $staging -Force | Out-Null

$excludedDirectoryNames = @(
    ".venv",
    ".pytest_cache",
    "__pycache__",
    "releases",
    "backups",
    ".git"
)

$excludedTopLevelPrefixes = @(
    "Sprint69_",
    "Sprint70_",
    "Sprint71_",
    "Sprint72_",
    "Sprint73_",
    "Sprint74_"
)

$allFiles = Get-ChildItem $ProjectRoot -Recurse -File | Where-Object {
    $relative = $_.FullName.Substring($ProjectRoot.Length).TrimStart("\")
    $parts = $relative -split "[\\/]"
    $top = $parts[0]

    $directoryExcluded = $false
    foreach ($part in $parts) {
        if ($excludedDirectoryNames -contains $part) {
            $directoryExcluded = $true
            break
        }
    }

    $prefixExcluded = $false
    foreach ($prefix in $excludedTopLevelPrefixes) {
        if ($top.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            $prefixExcluded = $true
            break
        }
    }

    -not $directoryExcluded `
        -and -not $prefixExcluded `
        -and $_.Extension -notin @(".pyc", ".bak")
}

foreach ($file in $allFiles) {
    $relative = $file.FullName.Substring($ProjectRoot.Length).TrimStart("\")
    $destination = Join-Path $staging $relative
    $destinationDirectory = Split-Path -Parent $destination
    New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
    Copy-Item $file.FullName $destination -Force
}

Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $snapshot -Force
$hash = (Get-FileHash $snapshot -Algorithm SHA256).Hash
"$hash  $releaseName.zip" | Set-Content -Path $shaFile -Encoding utf8

function Get-PassedCount {
    param([object[]]$Output)
    $text = $Output -join "`n"
    $matches = [regex]::Matches($text, "(\d+)\s+passed")
    if ($matches.Count -eq 0) {
        return $null
    }
    return [int]$matches[$matches.Count - 1].Groups[1].Value
}

$targetPassed = Get-PassedCount $targetOutput
$regressionPassed = Get-PassedCount $regressionOutput
$sourceFileCount = (Get-ChildItem $staging -Recurse -File).Count
$snapshotInfo = Get-Item $snapshot

$releaseRecord = [ordered]@{
    release = "Teknik Analiz V1.2"
    generated_at = (Get-Date).ToString("o")
    project_root = $ProjectRoot
    target_tests_passed = $targetPassed
    full_regression_passed = $regressionPassed
    system_check_ready = $true
    compileall_ok = $true
    source_file_count = $sourceFileCount
    snapshot_file = $snapshotInfo.Name
    snapshot_size_bytes = $snapshotInfo.Length
    snapshot_sha256 = $hash
    scope = @(
        "RSI/MACD divergence",
        "daily-weekly decision matrix",
        "signal outcome tracking",
        "indicator contribution analysis",
        "walk-forward calibration"
    )
    excluded_scope = @(
        "live market data",
        "order book",
        "scalping execution"
    )
}

$releaseRecord |
    ConvertTo-Json -Depth 6 |
    Set-Content -Path $releaseJson -Encoding utf8

Remove-Item $staging -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "TEKNİK ANALİZ V1.2 KAPANIŞI BAŞARILI"
Write-Host "Hedef test: $targetPassed"
Write-Host "Tam regresyon: $regressionPassed"
Write-Host "Snapshot: $snapshot"
Write-Host "SHA-256: $shaFile"
Write-Host "Release kaydı: $releaseJson"
