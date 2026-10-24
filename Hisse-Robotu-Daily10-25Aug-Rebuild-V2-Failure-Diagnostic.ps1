param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu",
    [string]$ReportPath = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Discovery = Join-Path $ProjectRoot "_discovery"

if ([string]::IsNullOrWhiteSpace($ReportPath)) {
    $candidate = Get-ChildItem -LiteralPath $Discovery `
        -Filter "Hisse-Robotu-Daily10-25Aug-Canonical-Session-Rebuild-V2-*.txt" `
        -File `
        | Sort-Object LastWriteTime -Descending `
        | Select-Object -First 1

    if ($null -eq $candidate) {
        throw "LATEST_25AUG_REBUILD_V2_REPORT_NOT_FOUND"
    }

    $ReportPath = $candidate.FullName
}

if (-not (Test-Path -LiteralPath $ReportPath)) {
    throw "REPORT_NOT_FOUND=$ReportPath"
}

Write-Host "=== HISSE ROBOTU — 25AUG REBUILD V2 FAILURE DIAGNOSTIC ==="
Write-Host "MODE=READ_ONLY"
Write-Host "PRODUCTION_MUTATION=NO"
Write-Host ("REPORT=" + $ReportPath)
Write-Host ""

$lines = @(Get-Content -LiteralPath $ReportPath -Encoding UTF8)
$joined = $lines -join "`n"

Write-Host "=== EXACT PYTHON EXCEPTION ==="

$traceIdx = -1
for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match '^Traceback \(most recent call last\):') {
        $traceIdx = $i
    }
}

if ($traceIdx -ge 0) {
    $end = [Math]::Min($lines.Count - 1, $traceIdx + 45)
    for ($i = $traceIdx; $i -le $end; $i++) {
        Write-Host ("{0:D4}: {1}" -f ($i + 1), $lines[$i])
    }
}
else {
    $errorHits = @()
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if (
            $lines[$i] -match 'REBUILD_(BLOCKED|CONTRACT_BLOCKED|POSTWRITE_FAIL):' -or
            $lines[$i] -match '(RuntimeError|ValueError|TypeError|KeyError|AttributeError|ImportError|ModuleNotFoundError|SyntaxError):'
        ) {
            $errorHits += $i
        }
    }

    if ($errorHits.Count -eq 0) {
        Write-Host "EXACT_EXCEPTION=NOT_FOUND"
    }
    else {
        foreach ($idx in $errorHits | Select-Object -Last 3) {
            $start = [Math]::Max(0, $idx - 6)
            $end = [Math]::Min($lines.Count - 1, $idx + 8)
            Write-Host ("--- EXCEPTION_CONTEXT_{0}_{1} ---" -f ($start + 1), ($end + 1))
            for ($j = $start; $j -le $end; $j++) {
                Write-Host ("{0:D4}: {1}" -f ($j + 1), $lines[$j])
            }
        }
    }
}

Write-Host ""
Write-Host "=== LAST SUCCESSFUL CHECKPOINTS ==="

$checkpointPatterns = @(
    "BASELINE17_EXACT=PASS",
    "PREVIOUS_TERMINAL_UNIVERSE_ACCEPTANCE=PROVEN",
    "PROVEN_EVIDENCE=",
    "LEDGER_RECONCILIATION=PASS",
    "CURRENT_TERMINAL_SNAPSHOT_REQUIRED=NO",
    "UNIVERSE25_COUNT=",
    "SOURCE=",
    "PROFILE=",
    "MODE=",
    "SELECTION_MODE=",
    "REMEMBERED_ROWS=",
    "CANONICAL_FULL_ROWS=",
    "PREFIX_RANK_PARITY=",
    "CROSS_CONTRACT_SAME_SESSION=",
    "OLD_SELECTED_ROWS=",
    "NEW_SELECTED_ROWS=",
    "MUTATION_NEEDED=",
    "25AUG_CANONICAL_PARITY=",
    "REBUILD_PYTHON_STAGE=PASS"
)

foreach ($line in $lines) {
    foreach ($p in $checkpointPatterns) {
        if ($line -like "*$p*") {
            Write-Host $line
            break
        }
    }
}

Write-Host ""
Write-Host "=== FINAL DIAGNOSTIC DECISION ==="

if ($joined -match "REBUILD_BLOCKED:PREVIOUSLY_PROVEN_TERMINAL_UNIVERSE_EVIDENCE_MISSING") {
    Write-Host "FAILURE_CLASS=PROVEN_ACCEPTANCE_REPORT_NOT_DISCOVERED"
    Write-Host "NEXT=DISCOVER_EXISTING_ACCEPTANCE_REPORT_NAMES_AND_MARKERS;DO_NOT_MUTATE_MEMORY"
}
elseif ($joined -match "REBUILD_BLOCKED:BASELINE17_EXACT_MISSING") {
    Write-Host "FAILURE_CLASS=BASELINE17_ARTIFACT_NOT_RECOVERED"
    Write-Host "NEXT=REUSE_PROVEN_BASELINE_ARTIFACT_PATH_OR_EMBED_VALIDATED_BASELINE_PAYLOAD;DO_NOT_MUTATE_MEMORY"
}
elseif ($joined -match "REBUILD_BLOCKED:LEDGER_RECONSTRUCTION_DIFF_MISMATCH") {
    Write-Host "FAILURE_CLASS=LEDGER_RECONSTRUCTION_GUARD_FAIL"
    Write-Host "NEXT=PRINT_BASELINE_COUNT_AND_LEDGER_DIFF_BEFORE_ANY_MUTATION"
}
elseif ($joined -match "REBUILD_BLOCKED:NO_EXISTING_25AUG_MEMORY") {
    Write-Host "FAILURE_CLASS=NO_25AUG_MEMORY_ANCHOR"
    Write-Host "NEXT=INVENTORY_RANKING_MEMORY_DATES_AND_CONTRACTS;DO_NOT_MUTATE"
}
elseif ($joined -match "REBUILD_BLOCKED:NO_NONBLANK_25AUG_CONTRACT") {
    Write-Host "FAILURE_CLASS=25AUG_CONTRACT_METADATA_BLANK"
    Write-Host "NEXT=INVENTORY_RAW_25AUG_MEMORY_ROWS;DO_NOT_MUTATE"
}
elseif ($joined -match "REBUILD_CONTRACT_BLOCKED:PREFIX_OR_EXACT_MATCH_COUNT=0") {
    Write-Host "FAILURE_CLASS=NO_PREFIX_PARITY_WITH_CANONICAL_REPLAY"
    Write-Host "NEXT=COMPARE_OLD_25AUG_RANK_PREFIX_TO_CANONICAL_REPLAY_RANK_BY_RANK;DO_NOT_MUTATE"
}
elseif ($joined -match "REBUILD_CONTRACT_BLOCKED:PREFIX_OR_EXACT_MATCH_COUNT=([2-9]|\d{2,})") {
    Write-Host "FAILURE_CLASS=AMBIGUOUS_PREFIX_PARITY"
    Write-Host "NEXT=DISAMBIGUATE_25AUG_SOURCE_PROFILE_GROUPS;DO_NOT_MUTATE"
}
elseif ($joined -match "REBUILD_CONTRACT_BLOCKED:CROSS_CONTRACT_SAME_SESSION_COUNT=") {
    Write-Host "FAILURE_CLASS=CROSS_CONTRACT_25AUG_CONTAMINATION"
    Write-Host "NEXT=INVENTORY_CONFLICTING_25AUG_ROWS_BEFORE_ANY_REWRITE"
}
elseif ($joined -match "REBUILD_BLOCKED:CANONICAL_RANKED_UNIVERSE_SIZE_INCONSISTENT") {
    Write-Host "FAILURE_CLASS=CANONICAL_METADATA_SIZE_MISMATCH"
    Write-Host "NEXT=DIAGNOSE_REPLAY_OBSERVATION_METADATA;DO_NOT_MUTATE"
}
elseif ($joined -match "REBUILD_BLOCKED:RAW_STORE_COUNT_MISMATCH") {
    Write-Host "FAILURE_CLASS=STORE_VS_RAW_JSONL_COUNT_MISMATCH"
    Write-Host "NEXT=INVENTORY_RAW_SELECTED_ROWS_AND_STORE_PARSE;DO_NOT_MUTATE"
}
elseif ($joined -match "REBUILD_POSTWRITE_FAIL:") {
    Write-Host "FAILURE_CLASS=POSTWRITE_VALIDATION_FAIL"
    Write-Host "NEXT=USE_EXACT_POSTWRITE_EXCEPTION_AS_PATCH_INPUT;MEMORY_ALREADY_ROLLED_BACK"
}
elseif ($joined -match "RuntimeError:") {
    Write-Host "FAILURE_CLASS=OTHER_RUNTIME_GUARD"
    Write-Host "NEXT=USE_EXACT_RUNTIMEERROR_LINE_AS_FIX_INPUT"
}
elseif ($joined -match "Traceback") {
    Write-Host "FAILURE_CLASS=PYTHON_EXCEPTION_OTHER"
    Write-Host "NEXT=USE_PRINTED_TRACEBACK_AS_EXACT_FIX_INPUT"
}
else {
    Write-Host "FAILURE_CLASS=UNCLASSIFIED"
    Write-Host "NEXT=PASTE_EXACT_PYTHON_EXCEPTION_AND_LAST_SUCCESSFUL_CHECKPOINTS"
}

Write-Host "25AUG_REBUILD_V2_FAILURE_DIAGNOSTIC=PASS"
