$ErrorActionPreference = "Stop"

$Root = (Get-Location).Path
$Discovery = Join-Path $Root "_discovery"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Out = Join-Path $Discovery "tefas_http_transport_contract_$Stamp.txt"

$HttpFile = Join-Path $Root "backend\app\news_center\official_source_http.py"

Write-Host ""
Write-Host "TEFAS_HTTP_TRANSPORT_CONTRACT"

if (-not (Test-Path $HttpFile)) {
    Write-Host "STATUS=STOP"
    Write-Host "REASON=OFFICIAL_HTTP_HELPER_NOT_FOUND"
    Write-Host "NETWORK_CALL=NO"
    Write-Host "SOURCE_MUTATION=NO"
    exit 1
}

$HashBefore = (Get-FileHash $HttpFile -Algorithm SHA256).Hash
$Lines = @(Get-Content $HttpFile -Encoding UTF8)

# lgili testleri bul.
$TestFiles = @(
    Get-ChildItem (Join-Path $Root "backend\tests") -Recurse -File -Filter "*.py" |
    Where-Object {
        Select-String `
            -Path $_.FullName `
            -Pattern "official_source_http","fetch_official_source_bytes" `
            -SimpleMatch `
            -Quiet `
            -ErrorAction SilentlyContinue
    }
)

$Log = New-Object System.Collections.Generic.List[string]

$Log.Add("TEFAS_HTTP_TRANSPORT_CONTRACT")
$Log.Add("HTTP_FILE=$HttpFile")
$Log.Add("")

$Log.Add("===== OFFICIAL_SOURCE_HTTP_BEGIN =====")

for ($i = 0; $i -lt $Lines.Count; $i++) {
    $Log.Add(("{0:D3}: {1}" -f ($i + 1), $Lines[$i]))
}

$Log.Add("===== OFFICIAL_SOURCE_HTTP_END =====")
$Log.Add("")
$Log.Add("===== RELATED_TESTS_BEGIN =====")

foreach ($Test in $TestFiles) {
    $Log.Add("")
    $Log.Add("TEST_FILE=$($Test.FullName)")

    $TestLines = @(Get-Content $Test.FullName -Encoding UTF8)

    for ($i = 0; $i -lt $TestLines.Count; $i++) {
        $Line = $TestLines[$i]

        if (
            $Line -match 'official_source_http' -or
            $Line -match 'fetch_official_source_bytes' -or
            $Line -match 'urlopen' -or
            $Line -match 'Request' -or
            $Line -match 'timeout' -or
            $Line -match 'User-Agent' -or
            $Line -match 'http'
        ) {
            $Log.Add(
                ("{0}:L{1:D3}: {2}" -f `
                    $Test.Name, `
                    ($i + 1), `
                    $Line.Trim())
            )
        }
    }
}

$Log.Add("===== RELATED_TESTS_END =====")

$Log | Set-Content $Out -Encoding UTF8

$HashAfter = (Get-FileHash $HttpFile -Algorithm SHA256).Hash

$SourceMutation = if ($HashBefore -eq $HashAfter) {
    "NO"
}
else {
    "YES"
}

# Fonksiyon / sınıf imzaları.
$Definitions = @(
    for ($i = 0; $i -lt $Lines.Count; $i++) {
        if ($Lines[$i] -match '^\s*(def|class)\s+([A-Za-z_][A-Za-z0-9_]*)') {
            [PSCustomObject]@{
                Line = $i + 1
                Kind = $Matches[1]
                Name = $Matches[2]
                Text = $Lines[$i].Trim()
            }
        }
    }
)

$TransportRefs = @(
    for ($i = 0; $i -lt $Lines.Count; $i++) {
        if (
            $Lines[$i] -match 'urllib' -or
            $Lines[$i] -match 'requests' -or
            $Lines[$i] -match 'httpx' -or
            $Lines[$i] -match 'urlopen' -or
            $Lines[$i] -match 'Request\(' -or
            $Lines[$i] -match 'method=' -or
            $Lines[$i] -match 'data=' -or
            $Lines[$i] -match 'headers' -or
            $Lines[$i] -match 'Content-Type'
        ) {
            [PSCustomObject]@{
                Line = $i + 1
                Text = $Lines[$i].Trim()
            }
        }
    }
)

Write-Host "HTTP_FILE=$HttpFile"
Write-Host "HTTP_LINE_COUNT=$($Lines.Count)"
Write-Host "DEFINITION_COUNT=$($Definitions.Count)"

foreach ($D in $Definitions) {
    Write-Host "DEF=L$($D.Line):$($D.Kind):$($D.Name):$($D.Text)"
}

Write-Host ""
Write-Host "TRANSPORT_REF_COUNT=$($TransportRefs.Count)"

foreach ($R in $TransportRefs) {
    Write-Host "TRANSPORT_REF=L$($R.Line):$($R.Text)"
}

Write-Host ""
Write-Host "RELATED_TEST_FILE_COUNT=$($TestFiles.Count)"

foreach ($T in $TestFiles) {
    Write-Host "TEST_FILE=$($T.FullName.Replace($Root + '\',''))"
}

Write-Host ""
Write-Host "===== OFFICIAL_SOURCE_HTTP_BEGIN ====="

for ($i = 0; $i -lt $Lines.Count; $i++) {
    Write-Host ("{0:D3}: {1}" -f ($i + 1), $Lines[$i])
}

Write-Host "===== OFFICIAL_SOURCE_HTTP_END ====="

Write-Host ""
Write-Host "NETWORK_CALL=NO"
Write-Host "SOURCE_MUTATION=$SourceMutation"

if ($SourceMutation -eq "NO") {
    Write-Host "STATUS=HTTP_TRANSPORT_CONTRACT_READY"
    Write-Host "NEXT=APPLY_MINIMAL_PROVIDER_MIGRATION"
}
else {
    Write-Host "STATUS=STOP"
    Write-Host "NEXT=RECOVERY_MODE"
}

Write-Host "FULL_LOG=$Out"
