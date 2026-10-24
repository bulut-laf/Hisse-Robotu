param(
    [Parameter(Mandatory = $false)]
    [ValidateSet("Hizli", "Tam")]
    [string]$Mod = "Hizli",

    [Parameter(Mandatory = $false)]
    [string]$Paket,

    [Parameter(Mandatory = $false)]
    [string]$HedefTest
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message"
}

function Fail {
    param([string]$Message)
    Write-Host ""
    Write-Error $Message
    exit 1
}

function Invoke-Checked {
    param(
        [string]$Description,
        [scriptblock]$Action
    )

    Write-Step $Description
    & $Action

    if ($LASTEXITCODE -ne 0) {
        Fail "$Description aşaması başarısız oldu."
    }
}

$PackagePatchPaths = @()

if ($Paket) {
    $ResolvedPackage = Resolve-Path -LiteralPath $Paket -ErrorAction Stop

    if ([System.IO.Path]::GetExtension($ResolvedPackage.Path) -ne ".zip") {
        Fail "Paket bir ZIP dosyası olmalıdır."
    }

    Add-Type -AssemblyName System.IO.Compression.FileSystem

    $Archive = [System.IO.Compression.ZipFile]::OpenRead($ResolvedPackage.Path)
    try {
        $PackagePatchPaths = @(
            $Archive.Entries |
                Where-Object {
                    -not [string]::IsNullOrWhiteSpace($_.Name) -and
                    $_.Name -like "apply_*.py"
                } |
                ForEach-Object {
                    Join-Path $ProjectRoot ($_.FullName.Replace("/", "\"))
                }
        )
    }
    finally {
        $Archive.Dispose()
    }

    Write-Step "Sprint paketi proje klasörüne çıkarılıyor"
    Expand-Archive -LiteralPath $ResolvedPackage.Path -DestinationPath $ProjectRoot -Force

    foreach ($PatchPath in $PackagePatchPaths) {
        if (-not (Test-Path -LiteralPath $PatchPath)) {
            Fail "Paket yaması çıkarılamadı: $PatchPath"
        }

        Invoke-Checked "Paket yaması uygulanıyor: $(Split-Path -Leaf $PatchPath)" {
            python $PatchPath
        }
    }
}
else {
    Write-Step "Paket verilmedi"
    Write-Host "Tarihî apply_*.py dosyaları yeniden çalıştırılmayacak."
}

if ($HedefTest) {
    Invoke-Checked "Hedef test çalıştırılıyor: $HedefTest" {
        python -m pytest $HedefTest -q
    }
}
elseif ($Mod -eq "Hizli") {
    Write-Step "Hızlı mod seçildi"
    Write-Host "Hedef test belirtilmediği için test çalıştırılmadı."
}

if ($Mod -eq "Tam") {
    Invoke-Checked "Tam regresyon testleri çalıştırılıyor" {
        python -m pytest -q
    }
}

Write-Host ""
Write-Host "İŞLEM BAŞARILI"
Write-Host "Mod: $Mod"
if ($Paket) {
    Write-Host "Paket: $Paket"
}
if ($HedefTest) {
    Write-Host "Hedef test: $HedefTest"
}
