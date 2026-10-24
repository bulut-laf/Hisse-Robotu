param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Copy-Item `
    "$packageRoot\Close-Teknik-Analiz-V1.2.ps1" `
    "$ProjectRoot\Close-Teknik-Analiz-V1.2.ps1" `
    -Force

Set-Location $ProjectRoot

Write-Host "Kapanış betiği güncellendi."
Write-Host "Şimdi çalıştırın: & `".\Close-Teknik-Analiz-V1.2.ps1`""
