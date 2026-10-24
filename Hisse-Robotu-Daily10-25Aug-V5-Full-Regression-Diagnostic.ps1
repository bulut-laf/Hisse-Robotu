param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu",
    [string]$ReportPath = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Discovery = Join-Path $ProjectRoot "_discovery"
$MemoryFile = Join-Path $ProjectRoot "data\ranking_memory\rank_observations.jsonl"

if (-not (Test-Path -LiteralPath $MemoryFile)) {
    throw "RANKING_MEMORY_MISSING=$MemoryFile"
}

$shaBefore = (Get-FileHash -LiteralPath $MemoryFile -Algorithm SHA256).Hash

if ([string]::IsNullOrWhiteSpace($ReportPath)) {
    $latest = Get-ChildItem -LiteralPath $Discovery `
        -Filter "Hisse-Robotu-Daily10-25Aug-Canonical-Session-Rebuild-V5-*.txt" `
        -File `
        | Sort-Object LastWriteTime -Descending `
        | Select-Object -First 1

    if ($null -eq $latest) {
        throw "LATEST_V5_REPORT_NOT_FOUND"
    }

    $ReportPath = $latest.FullName
}

if (-not (Test-Path -LiteralPath $ReportPath)) {
    throw "REPORT_NOT_FOUND=$ReportPath"
}

Write-Host "=== HISSE ROBOTU — 25AUG V5 FULL REGRESSION DIAGNOSTIC ==="
Write-Host "MODE=READ_ONLY"
Write-Host "PRODUCTION_MUTATION=NO"
Write-Host ("REPORT=" + $ReportPath)
Write-Host ("RANKING_MEMORY_SHA_BEFORE=" + $shaBefore)
Write-Host ""

$lines = @(Get-Content -LiteralPath $ReportPath -Encoding UTF8)

# ------------------------------------------------------------------
# Extract pytest failed/error nodes from short summary.
# ------------------------------------------------------------------
$failedNodes = New-Object System.Collections.Generic.List[string]

foreach ($line in $lines) {
    if ($line -match '^(FAILED|ERROR)\s+([^\s]+::[^\s]+)') {
        $failedNodes.Add($Matches[2])
    }
}

$uniqueNodes = @($failedNodes | Select-Object -Unique)

Write-Host "=== FAILED TEST NODES ==="
if ($uniqueNodes.Count -eq 0) {
    Write-Host "FAILED_NODE=NOT_FOUND"
} else {
    foreach ($node in $uniqueNodes) {
        Write-Host ("FAILED_NODE=" + $node)
    }
}
Write-Host ("FAILED_NODE_COUNT=" + $uniqueNodes.Count)

# ------------------------------------------------------------------
# Print pytest failure sections and assertion evidence.
# ------------------------------------------------------------------
Write-Host ""
Write-Host "=== PYTEST FAILURE EVIDENCE ==="

$failureHeaderIdx = -1
$summaryIdx = -1

for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match '=+\s+FAILURES\s+=+') {
        $failureHeaderIdx = $i
    }
    if ($lines[$i] -match '=+\s+short test summary info\s+=+') {
        $summaryIdx = $i
    }
}

if ($failureHeaderIdx -ge 0) {
    $end = if ($summaryIdx -gt $failureHeaderIdx) {
        $summaryIdx - 1
    } else {
        [Math]::Min($lines.Count - 1, $failureHeaderIdx + 350)
    }

    for ($i = $failureHeaderIdx; $i -le $end; $i++) {
        Write-Host $lines[$i]
    }
} else {
    Write-Host "FAILURE_SECTION=NOT_FOUND"
    Write-Host ""
    Write-Host "=== REPORT TAIL ==="
    $start = [Math]::Max(0, $lines.Count - 220)
    for ($i = $start; $i -lt $lines.Count; $i++) {
        Write-Host $lines[$i]
    }
}

# ------------------------------------------------------------------
# For each failed test node, print the exact test function source seam.
# ------------------------------------------------------------------
Write-Host ""
Write-Host "=== FAILED TEST SOURCE SEAMS ==="

foreach ($node in $uniqueNodes) {
    $parts = $node -split '::'
    if ($parts.Count -lt 2) {
        continue
    }

    $relPath = $parts[0] -replace '/', '\'
    $testName = $parts[1]
    $filePath = Join-Path $ProjectRoot $relPath

    Write-Host ""
    Write-Host ("--- NODE=" + $node + " ---")
    Write-Host ("FILE=" + $filePath)

    if (-not (Test-Path -LiteralPath $filePath)) {
        Write-Host "SOURCE_FILE=NOT_FOUND"
        continue
    }

    $src = @(Get-Content -LiteralPath $filePath -Encoding UTF8)
    $match = $src | Select-String `
        -Pattern ("^\s*(async\s+)?def\s+" + [regex]::Escape($testName) + "\b") `
        | Select-Object -First 1

    if ($null -eq $match) {
        Write-Host "TEST_FUNCTION=NOT_FOUND"
        continue
    }

    $start = [Math]::Max(0, $match.LineNumber - 4)
    $end = [Math]::Min($src.Count - 1, $match.LineNumber + 55)

    for ($i = $start; $i -le $end; $i++) {
        Write-Host ("{0:D4}: {1}" -f ($i + 1), $src[$i])
    }
}

# ------------------------------------------------------------------
# Heuristic classification only; no mutation.
# ------------------------------------------------------------------
Write-Host ""
Write-Host "=== FINAL DIAGNOSTIC CLASSIFICATION ==="

$nodeText = ($uniqueNodes -join "`n")
$reportText = ($lines -join "`n")

if ($uniqueNodes.Count -eq 0) {
    Write-Host "REGRESSION_FAILURE_CLASS=FAILED_NODE_NOT_EXTRACTED"
    Write-Host "NEXT=USE_PRINTED_FAILURE_SECTION_OR_REPORT_TAIL_AS_EXACT_INPUT"
}
elseif ($uniqueNodes.Count -gt 1) {
    Write-Host "REGRESSION_FAILURE_CLASS=MULTIPLE_FAILED_NODES"
    Write-Host "NEXT=REVIEW_EACH_FAILED_NODE;PATCH_ONLY_SHARED_PROVEN_CONTRACT_IF_ONE_EXISTS"
}
elseif (
    $nodeText -match 'ranking|daily_early|dashboard|market_scanner|visibility'
) {
    Write-Host "REGRESSION_FAILURE_CLASS=RANKING_RELATED_SINGLE_NODE"
    Write-Host "NEXT=PATCH_ONLY_EXACT_FAILED_TEST_OR_DATA-ISOLATION_CONTRACT_AFTER_SOURCE_REVIEW"
}
else {
    Write-Host "REGRESSION_FAILURE_CLASS=NON_RANKING_SINGLE_NODE"
    Write-Host "NEXT=DO_NOT_CHANGE_25AUG_REBUILD_DESIGN;REVIEW_EXACT_UNRELATED_FAILURE"
}

if ($reportText -match 'passed') {
    Write-Host "PYTEST_SUMMARY_PRESENT=YES"
} else {
    Write-Host "PYTEST_SUMMARY_PRESENT=NO"
}

$shaAfter = (Get-FileHash -LiteralPath $MemoryFile -Algorithm SHA256).Hash
Write-Host ("RANKING_MEMORY_SHA_AFTER=" + $shaAfter)

if ($shaAfter -ne $shaBefore) {
    throw "READ_ONLY_DIAGNOSTIC_GUARD_FAIL:RANKING_MEMORY_CHANGED"
}

Write-Host "RANKING_MEMORY_UNCHANGED=YES"
Write-Host "25AUG_V5_FULL_REGRESSION_DIAGNOSTIC=PASS"
