$ErrorActionPreference = "Stop"

$Root = (Get-Location).Path
$Discovery = Join-Path $Root "_discovery"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Out = Join-Path $Discovery "tefas_exact_adapter_contract_$Stamp.txt"

function Get-SourceSignature {
    $Rows = @(
        Get-ChildItem $Root -Recurse -File |
        Where-Object {
            $_.Extension -in @(".py",".json",".toml",".yaml",".yml",".js",".ts") -and
            $_.FullName -notmatch '[\\/](\.venv|venv|node_modules|_discovery|\.git|dist|build)[\\/]'
        } |
        Sort-Object FullName |
        ForEach-Object {
            "$($_.FullName)|$((Get-FileHash $_.FullName -Algorithm SHA256).Hash)"
        }
    )

    return (($Rows -join "`n") | ForEach-Object {
        $Bytes = [System.Text.Encoding]::UTF8.GetBytes($_)
        $Sha = [System.Security.Cryptography.SHA256]::Create()
        ([BitConverter]::ToString($Sha.ComputeHash($Bytes))).Replace("-","")
    })
}

$BeforeSignature = Get-SourceSignature

$Adapter = Join-Path $Root "backend\app\funds\tefas_adapter.py"

if (-not (Test-Path $Adapter)) {
    Write-Host ""
    Write-Host "TEFAS_EXACT_ADAPTER_CONTRACT"
    Write-Host "STATUS=STOP"
    Write-Host "REASON=TEFAS_ADAPTER_NOT_FOUND"
    Write-Host "NETWORK_CALL=NO"
    Write-Host "SOURCE_MUTATION=NO"
    exit 1
}

$AdapterContent = @(Get-Content $Adapter -Encoding UTF8)

$Definitions = @(
    for ($i = 0; $i -lt $AdapterContent.Count; $i++) {
        if ($AdapterContent[$i] -match '^\s*(def|class)\s+([A-Za-z_][A-Za-z0-9_]*)') {
            [PSCustomObject]@{
                Line = $i + 1
                Type = $Matches[1]
                Name = $Matches[2]
                Text = $AdapterContent[$i].Trim()
            }
        }
    }
)

$FunctionNames = @(
    $Definitions |
    Where-Object { $_.Type -eq "def" } |
    Select-Object -ExpandProperty Name -Unique
)

$PythonFiles = @(
    Get-ChildItem (Join-Path $Root "backend") -Recurse -File -Filter "*.py" |
    Where-Object {
        $_.FullName -notmatch '[\\/](\.venv|venv|_discovery|\.git)[\\/]' -and
        $_.FullName -ne $Adapter
    }
)

$Callers = @()

foreach ($File in $PythonFiles) {
    $Hits = @(
        Select-String `
            -Path $File.FullName `
            -Pattern @(
                "tefas_adapter",
                "canonical_tefas_fund_id",
                "map_tefas_rows",
                "fetch_tefas",
                "TEFAS"
            ) `
            -SimpleMatch `
            -ErrorAction SilentlyContinue
    )

    foreach ($Hit in $Hits) {
        $Callers += [PSCustomObject]@{
            File = $Hit.Path
            Line = $Hit.LineNumber
            Text = $Hit.Line.Trim()
        }
    }
}

$Callers = @(
    $Callers |
    Sort-Object File,Line,Text -Unique
)

$RelevantTests = @(
    $Callers |
    Where-Object {
        $_.File -match '[\\/]tests[\\/]' -and
        (
            $_.Text -match 'tefas|map_tefas_rows|canonical_tefas_fund_id'
        )
    }
)

$LegacyHits = @()

foreach ($Pattern in @(
    "BindHistoryInfo",
    "BindHistoryAllocation",
    "fundturkey.com.tr",
    "fonGnlBlgSiraliGetir"
)) {
    $LegacyHits += @(
        Select-String `
            -Path $Adapter `
            -Pattern $Pattern `
            -SimpleMatch `
            -ErrorAction SilentlyContinue |
        ForEach-Object {
            [PSCustomObject]@{
                Pattern = $Pattern
                Line = $_.LineNumber
                Text = $_.Line.Trim()
            }
        }
    )
}

$NetworkHits = @()

foreach ($Pattern in @(
    "fetch_official_source_bytes",
    "requests",
    "urllib",
    "urlopen",
    "http",
    "endpoint",
    "payload",
    "json"
)) {
    $NetworkHits += @(
        Select-String `
            -Path $Adapter `
            -Pattern $Pattern `
            -SimpleMatch `
            -ErrorAction SilentlyContinue |
        ForEach-Object {
            [PSCustomObject]@{
                Pattern = $Pattern
                Line = $_.LineNumber
                Text = $_.Line.Trim()
            }
        }
    )
}

$NetworkHits = @(
    $NetworkHits |
    Sort-Object Line,Pattern,Text -Unique
)

# Full source evidence
$Log = New-Object System.Collections.Generic.List[string]

$Log.Add("TEFAS_EXACT_ADAPTER_CONTRACT")
$Log.Add("ADAPTER=$Adapter")
$Log.Add("")

$Log.Add("[FULL_TEFAS_ADAPTER]")

for ($i = 0; $i -lt $AdapterContent.Count; $i++) {
    $Log.Add(("{0:D4}: {1}" -f ($i + 1), $AdapterContent[$i]))
}

$Log.Add("")
$Log.Add("[DEFINITIONS]")

foreach ($D in $Definitions) {
    $Log.Add("L$($D.Line) $($D.Type) $($D.Name) | $($D.Text)")
}

$Log.Add("")
$Log.Add("[CALLERS]")

foreach ($C in $Callers) {
    $Log.Add("$($C.File):$($C.Line) | $($C.Text)")
}

$Log.Add("")
$Log.Add("[LEGACY_REFS]")

foreach ($H in $LegacyHits) {
    $Log.Add("L$($H.Line) $($H.Pattern) | $($H.Text)")
}

$Log.Add("")
$Log.Add("[NETWORK_REFS]")

foreach ($H in $NetworkHits) {
    $Log.Add("L$($H.Line) $($H.Pattern) | $($H.Text)")
}

$Log | Set-Content $Out -Encoding UTF8

$AfterSignature = Get-SourceSignature

$SourceMutation = if ($BeforeSignature -eq $AfterSignature) {
    "NO"
}
else {
    "YES"
}

$Runner = Get-ChildItem $Root -Recurse -File -Filter "scheduled_operation_phase_runner.py" |
    Where-Object {
        $_.FullName -notmatch '[\\/](\.venv|venv|node_modules|_discovery|\.git)[\\/]'
    } |
    Select-Object -First 1

Write-Host ""
Write-Host "TEFAS_EXACT_ADAPTER_CONTRACT"
Write-Host "ADAPTER=$Adapter"
Write-Host "ADAPTER_LINE_COUNT=$($AdapterContent.Count)"
Write-Host "DEFINITION_COUNT=$($Definitions.Count)"

foreach ($D in $Definitions) {
    Write-Host "DEF=L$($D.Line):$($D.Type):$($D.Name)"
}

Write-Host ""
Write-Host "NETWORK_REF_COUNT=$($NetworkHits.Count)"

foreach ($H in ($NetworkHits | Select-Object -First 30)) {
    Write-Host "NETWORK_REF=L$($H.Line):$($H.Text)"
}

Write-Host ""
Write-Host "LEGACY_REF_COUNT=$($LegacyHits.Count)"

foreach ($H in $LegacyHits) {
    Write-Host "LEGACY_REF=L$($H.Line):$($H.Pattern):$($H.Text)"
}

Write-Host ""
Write-Host "CALLER_COUNT=$($Callers.Count)"

foreach ($C in ($Callers | Select-Object -First 40)) {
    $Relative = $C.File.Replace($Root + "\", "")
    Write-Host "CALLER=$Relative`:L$($C.Line):$($C.Text)"
}

Write-Host ""
Write-Host "RELEVANT_TEST_REF_COUNT=$($RelevantTests.Count)"

foreach ($T in ($RelevantTests | Select-Object -First 30)) {
    $Relative = $T.File.Replace($Root + "\", "")
    Write-Host "TEST_REF=$Relative`:L$($T.Line):$($T.Text)"
}

Write-Host ""
Write-Host "IMMUTABLE_RUNNER_PRESENT=$([bool]$Runner)"
Write-Host "NETWORK_CALL=NO"
Write-Host "SOURCE_MUTATION=$SourceMutation"

if ($SourceMutation -eq "NO") {
    Write-Host "STATUS=EXACT_CONTRACT_READY"
    Write-Host "NEXT=MINIMAL_PROVIDER_MIGRATION"
}
else {
    Write-Host "STATUS=STOP"
    Write-Host "NEXT=RECOVERY_MODE"
}

Write-Host "FULL_LOG=$Out"
