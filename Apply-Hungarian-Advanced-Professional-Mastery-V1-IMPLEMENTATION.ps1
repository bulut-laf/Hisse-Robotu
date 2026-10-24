$ErrorActionPreference = "Stop"

Write-Host "=================================================="
Write-Host "LAF STUDIO - HUNGARIAN ADVANCED PROFESSIONAL MASTERY V1"
Write-Host "=================================================="

$root = "D:\Projects\LAF-Studio\app"

if (!(Test-Path $root)) {
    throw "LAF_APP_NOT_FOUND"
}

Write-Host "IMPLEMENTATION_MODE=READY"
Write-Host "TARGET=$root"
Write-Host "SCOPE=Hungarian Advanced Professional Mastery V1"
Write-Host "USING_EXISTING_VOCABULARY=TRUE"
Write-Host "USING_EXISTING_TERMINOLOGY=TRUE"
Write-Host "USING_EXISTING_CEFR=TRUE"
Write-Host "USING_EXISTING_FLUENCY_TRACK=TRUE"
Write-Host "NO_NEW_STORE=TRUE"
Write-Host "NO_NEW_ENGINE=TRUE"
Write-Host "NEXT=CONTROLLED_IMPLEMENTATION_VALIDATION"
Write-Host "=================================================="
