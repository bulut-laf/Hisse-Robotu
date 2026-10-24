$ErrorActionPreference = "Stop"

Write-Host "LAF Studio Sprint 1765-1767"

Set-Location "$PSScriptRoot\app"

npm test
npm run build
