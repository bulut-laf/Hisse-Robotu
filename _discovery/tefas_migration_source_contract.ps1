$ErrorActionPreference = "Stop"

$Root      = (Get-Location).Path
$Discovery = Join-Path $Root "_discovery"
$Stamp     = Get-Date -Format "yyyyMMdd-HHmmss"
$FullLog   = Join-Path $Discovery "tefas_migration_source_contract_$Stamp.txt"

$Adapter = Join-Path $Root "backend\app\funds\tefas_adapter.py"
$Test    = Join-Path $Root "backend\tests\test_fund_data_contract_v1.py"

Write-Host ""
Write-Host "TEFAS_MIGRATION_SOURCE_CONTRACT"

if (-not (Test-Path $Adapter)) {
    Write-Host "STATUS=STOP"
    Write-Host "REASON=ADAPTER_NOT_FOUND"
    Write-Host "SOURCE_MUTATION=NO"
    exit 1
}

if (-not (Test-Path $Test)) {
    Write-Host "STATUS=STOP"
    Write-Host "REASON=DATA_CONTRACT_TEST_NOT_FOUND"
    Write-Host "SOURCE_MUTATION=NO"
    exit 1
}

$AdapterHashBefore = (Get-FileHash $Adapter -Algorithm SHA256).Hash
$TestHashBefore    = (Get-FileHash $Test -Algorithm SHA256).Hash

$AdapterLines = @(Get-Content $Adapter -Encoding UTF8)
$TestLines    = @(Get-Content $Test -Encoding UTF8)

$Log = New-Object System.Collections.Generic.List[string]

$Log.Add("TEFAS_MIGRATION_SOURCE_CONTRACT")
$Log.Add("ADAPTER=$Adapter")
$Log.Add("TEST=$Test")
$Log.Add("")

$Log.Add("===== ADAPTER_BEGIN =====")
for ($i = 0; $i -lt $AdapterLines.Count; $i++) {
    $Log.Add(("{0:D3}: {1}" -f ($i + 1), $AdapterLines[$i]))
}
$Log.Add("===== ADAPTER_END =====")

$Log.Add("")
$Log.Add("===== DATA_CONTRACT_TEST_BEGIN =====")
for ($i = 0; $i -lt $TestLines.Count; $i++) {
    $Log.Add(("{0:D3}: {1}" -f ($i + 1), $TestLines[$i]))
}
$Log.Add("===== DATA_CONTRACT_TEST_END =====")

# ------------------------------------------------------------
# Local funds dependencies referenced directly by tefas_adapter
# ------------------------------------------------------------

$DependencyPaths = New-Object System.Collections.Generic.List[string]

foreach ($Line in $AdapterLines) {

    if ($Line -match '^\s*from\s+\.(?<module>[A-Za-z0-9_]+)\s+import\s+') {
        $Path = Join-Path $Root (
            "backend\app\funds\" + $Matches["module"] + ".py"
        )

        if (Test-Path $Path) {
            if (-not $DependencyPaths.Contains($Path)) {
                $DependencyPaths.Add($Path)
            }
        }
    }

    if ($Line -match '^\s*from\s+backend\.app\.funds\.(?<module>[A-Za-z0-9_]+)\s+import\s+') {
        $Path = Join-Path $Root (
            "backend\app\funds\" + $Matches["module"] + ".py"
        )

        if (Test-Path $Path) {
            if (-not $DependencyPaths.Contains($Path)) {
                $DependencyPaths.Add($Path)
            }
        }
    }
}

$Log.Add("")
$Log.Add("===== LOCAL_DEPENDENCY_SIGNATURES =====")

foreach ($Dep in $DependencyPaths) {

    $Log.Add("DEPENDENCY=$Dep")

    $DepLines = @(Get-Content $Dep -Encoding UTF8)

    for ($i = 0; $i -lt $DepLines.Count; $i++) {

        $Line = $DepLines[$i]

        if (
            $Line -match '^\s*(class|def)\s+' -or
            $Line -match '^\s*@dataclass' -or
            $Line -match '^\s*[A-Za-z_][A-Za-z0-9_]*\s*:\s*' -or
            $Line -match '^\s*[A-Za-z_][A-Za-z0-9_]*\s*='
        ) {
            $Log.Add(
                ("{0}:L{1:D3}: {2}" -f `
                    [System.IO.Path]::GetFileName($Dep), `
                    ($i + 1), `
                    $Line.Trim())
            )
        }
    }

    $Log.Add("")
}

$Log | Set-Content $FullLog -Encoding UTF8

$AdapterHashAfter = (Get-FileHash $Adapter -Algorithm SHA256).Hash
$TestHashAfter    = (Get-FileHash $Test -Algorithm SHA256).Hash

$SourceMutation = "NO"

if ($AdapterHashBefore -ne $AdapterHashAfter) {
    $SourceMutation = "YES"
}

if ($TestHashBefore -ne $TestHashAfter) {
    $SourceMutation = "YES"
}

# ------------------------------------------------------------
# Compact but sufficient terminal evidence
# ------------------------------------------------------------

Write-Host "ADAPTER_LINE_COUNT=$($AdapterLines.Count)"
Write-Host "TEST_LINE_COUNT=$($TestLines.Count)"
Write-Host "LOCAL_DEPENDENCY_COUNT=$($DependencyPaths.Count)"

Write-Host ""
Write-Host "===== ADAPTER_BEGIN ====="

for ($i = 0; $i -lt $AdapterLines.Count; $i++) {
    Write-Host ("{0:D3}: {1}" -f ($i + 1), $AdapterLines[$i])
}

Write-Host "===== ADAPTER_END ====="

Write-Host ""
Write-Host "===== DATA_CONTRACT_TEST_BEGIN ====="

for ($i = 0; $i -lt $TestLines.Count; $i++) {
    Write-Host ("{0:D3}: {1}" -f ($i + 1), $TestLines[$i])
}

Write-Host "===== DATA_CONTRACT_TEST_END ====="

Write-Host ""
Write-Host "DEPENDENCIES=$(
    ($DependencyPaths | ForEach-Object {
        [System.IO.Path]::GetFileName($_)
    }) -join ','
)"

Write-Host "NETWORK_CALL=NO"
Write-Host "SOURCE_MUTATION=$SourceMutation"

if ($SourceMutation -eq "NO") {
    Write-Host "STATUS=MIGRATION_SOURCE_CONTRACT_READY"
    Write-Host "NEXT=APPLY_MINIMAL_PROVIDER_MIGRATION"
}
else {
    Write-Host "STATUS=STOP"
    Write-Host "NEXT=RECOVERY_MODE"
}

Write-Host "FULL_LOG=$FullLog"
