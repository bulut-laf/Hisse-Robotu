param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu",
    [string]$CaptureV2Script = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Dashboard = Join-Path $ProjectRoot "backend\dashboard.py"
$LegacyTest = Join-Path $ProjectRoot "backend\tests\test_ranking_memory.py"
$CaptureTest = Join-Path $ProjectRoot "backend\tests\test_ranking_memory_full_research_capture_v2.py"
$Discovery = Join-Path $ProjectRoot "_discovery"

foreach ($p in @($Python, $Dashboard, $LegacyTest, $Discovery)) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "REQUIRED_PATH_MISSING=$p"
    }
}

if ([string]::IsNullOrWhiteSpace($CaptureV2Script)) {
    $projectCandidate = Join-Path $ProjectRoot "Hisse-Robotu-Daily10-Full-Research-Capture-V2.ps1"

    if (Test-Path -LiteralPath $projectCandidate) {
        $CaptureV2Script = $projectCandidate
    }
    else {
        $downloadCandidate = Get-ChildItem "$env:USERPROFILE\Downloads" `
            -Filter "Hisse-Robotu-Daily10-Full-Research-Capture-V2*.ps1" `
            -File `
            -ErrorAction SilentlyContinue `
            | Sort-Object LastWriteTime -Descending `
            | Select-Object -First 1

        if ($null -ne $downloadCandidate) {
            $CaptureV2Script = $downloadCandidate.FullName
        }
    }
}

if ([string]::IsNullOrWhiteSpace($CaptureV2Script) -or -not (Test-Path -LiteralPath $CaptureV2Script)) {
    throw "CAPTURE_V2_SCRIPT_NOT_FOUND"
}

$latestReport = Get-ChildItem -LiteralPath $Discovery `
    -Filter "Hisse-Robotu-Daily10-Full-Research-Capture-V2-*.txt" `
    -File `
    | Sort-Object LastWriteTime -Descending `
    | Select-Object -First 1

if ($null -eq $latestReport) {
    throw "LATEST_CAPTURE_V2_REPORT_NOT_FOUND"
}

$reportText = [System.IO.File]::ReadAllText($latestReport.FullName)
$failedLines = @(
    $reportText -split "`r?`n" |
    Where-Object { $_ -match '^FAILED\s+' }
)

$expectedNode = "backend/tests/test_ranking_memory.py::test_dashboard_observes_full_research_rows_before_visible_filter"
$matching = @(
    $failedLines |
    Where-Object { $_ -like "FAILED $expectedNode*" }
)

$uniqueFailedNodes = @(
    $failedLines |
    ForEach-Object {
        if ($_ -match '^FAILED\s+(.+?)(?:\s+-\s+.*)?$') {
            $matches[1]
        }
    } |
    Sort-Object -Unique
)

Write-Host "=== HISSE ROBOTU — CAPTURE V2 LEGACY CONTRACT RECOVERY V1 ==="
Write-Host "MODE=CONTROLLED_TEST_CONTRACT_REPAIR_PLUS_CAPTURE_REAPPLY"
Write-Host "RANKING_MEMORY_DATA_MUTATION=NO"
Write-Host ("SOURCE_REPORT=" + $latestReport.FullName)
Write-Host ("CAPTURE_V2_SCRIPT=" + $CaptureV2Script)
Write-Host ""

Write-Host "=== FAILED NODE PREFLIGHT ==="
$failedLines | ForEach-Object { Write-Host $_ }

if ($matching.Count -lt 1) {
    Write-Host "FAIL-CLOSED=EXPECTED_LEGACY_NODE_NOT_PRESENT"
    Write-Host "MUTATION=NO"
    throw "LEGACY_RECOVERY_WRONG_FAILED_NODE"
}

if ($uniqueFailedNodes.Count -ne 1 -or $uniqueFailedNodes[0] -ne $expectedNode) {
    Write-Host "FAIL-CLOSED=MORE_THAN_ONE_OR_DIFFERENT_FAILED_NODE"
    Write-Host "UNIQUE_FAILED_NODES=$($uniqueFailedNodes.Count)"
    $uniqueFailedNodes | ForEach-Object { Write-Host ("NODE=" + $_) }
    Write-Host "MUTATION=NO"
    throw "LEGACY_RECOVERY_AMBIGUOUS_FAILED_SET"
}

Write-Host "EXACT_FAILED_NODE=PROVEN"
Write-Host ("NODE=" + $expectedNode)

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$rollback = Join-Path $ProjectRoot "_rollback\daily10-capture-v2-legacy-contract-recovery-$stamp"
$report = Join-Path $Discovery "Hisse-Robotu-Daily10-Capture-V2-Legacy-Contract-Recovery-V1-$stamp.txt"

New-Item -ItemType Directory -Force -Path $rollback | Out-Null

$legacyBackup = Join-Path $rollback "test_ranking_memory.py"
$dashboardBackup = Join-Path $rollback "dashboard.py"

Copy-Item -LiteralPath $LegacyTest -Destination $legacyBackup -Force
Copy-Item -LiteralPath $Dashboard -Destination $dashboardBackup -Force

$captureTestExisted = Test-Path -LiteralPath $CaptureTest
if ($captureTestExisted) {
    Copy-Item -LiteralPath $CaptureTest -Destination (Join-Path $rollback "test_ranking_memory_full_research_capture_v2.py") -Force
}

function Restore-All {
    Copy-Item -LiteralPath $legacyBackup -Destination $LegacyTest -Force
    Copy-Item -LiteralPath $dashboardBackup -Destination $Dashboard -Force

    if ($captureTestExisted) {
        Copy-Item `
            -LiteralPath (Join-Path $rollback "test_ranking_memory_full_research_capture_v2.py") `
            -Destination $CaptureTest `
            -Force
    }
    elseif (Test-Path -LiteralPath $CaptureTest) {
        Remove-Item -LiteralPath $CaptureTest -Force
    }

    Write-Host "ROLLBACK=SUCCESS"
    Write-Host "PRODUCTION_STATUS=PRE_RECOVERY_RESTORED"
}

$tmp = Join-Path $env:TEMP "hisse_daily10_legacy_contract_patch_v1.py"

try {
    $patchCode = @'
from __future__ import annotations

import ast
import hashlib
import sys
from pathlib import Path

path = Path(sys.argv[1])
source = path.read_text(encoding="utf-8")
tree = ast.parse(source)
lines = source.splitlines(keepends=True)

target_name = "test_dashboard_observes_full_research_rows_before_visible_filter"

matches = [
    node
    for node in tree.body
    if isinstance(node, ast.FunctionDef) and node.name == target_name
]

if len(matches) != 1:
    raise RuntimeError(
        f"FAIL-CLOSED:EXPECTED_ONE_TARGET_TEST_FUNCTION;FOUND={len(matches)}"
    )

fn = matches[0]
old_body = ast.get_source_segment(source, fn) or ""

if "rows=_three_all_rows" not in old_body.replace(" ", ""):
    raise RuntimeError(
        "FAIL-CLOSED:STALE_ROWS_ASSERTION_NOT_PRESENT_IN_TARGET_FUNCTION"
    )

if "observations_from_research_rows" not in old_body:
    raise RuntimeError(
        "FAIL-CLOSED:OBSERVATION_CONTRACT_NOT_PRESENT_IN_TARGET_FUNCTION"
    )

replacement = """def test_dashboard_observes_full_research_rows_before_visible_filter():
    root = Path(__file__).resolve().parents[2]
    text = (root / "backend" / "dashboard.py").read_text(encoding="utf-8")

    marker = "RANKING_JUMP_V1_BLOCK1"
    assert marker in text

    observation = text.index("observations_from_research_rows(")
    filtered = text.index("kayitlar = [", observation)
    dedicated = text.rfind("_ranking_memory_rows = tuple(", 0, observation)

    assert dedicated >= 0
    assert dedicated < observation < filtered

    capture_segment = text[dedicated:filtered]
    compact_capture = capture_segment.replace(" ", "").replace("\\n", "")

    assert "sonuc.filtrelenmis.adaylar" in capture_segment
    assert "rows=_ranking_memory_rows" in compact_capture
    assert "rows=_three_all_rows" not in compact_capture
    assert "ranked_universe_size" not in text[observation:filtered]
"""

def char_index(line_no: int, utf8_col: int) -> int:
    prefix = "".join(lines[: line_no - 1])
    line = lines[line_no - 1]
    b = line.encode("utf-8")
    chars = b[:utf8_col].decode("utf-8")
    return len(prefix) + len(chars)

start = char_index(fn.lineno, fn.col_offset)
end = char_index(fn.end_lineno, fn.end_col_offset)

patched = source[:start] + replacement + source[end:]

ast.parse(patched)

path.write_text(patched, encoding="utf-8", newline="")

print(f"PATCHED_TEST={path}")
print(f"SHA_BEFORE={hashlib.sha256(source.encode('utf-8')).hexdigest()}")
print(f"SHA_AFTER={hashlib.sha256(path.read_bytes()).hexdigest()}")
print("OLD_CONTRACT=rows=_three_all_rows")
print("NEW_CONTRACT=dedicated _ranking_memory_rows from sonuc.filtrelenmis.adaylar")
print("LEGACY_TEST_CONTRACT_PATCH=PASS")
'@

    [System.IO.File]::WriteAllText(
        $tmp,
        $patchCode,
        (New-Object System.Text.UTF8Encoding($false))
    )

    Write-Host ""
    Write-Host "=== PATCH EXACT LEGACY TEST CONTRACT ==="

    $patchOutput = & $Python $tmp $LegacyTest 2>&1
    $patchExit = $LASTEXITCODE
    $patchOutput | ForEach-Object { Write-Host $_ }

    if ($patchExit -ne 0) {
        Restore-All
        throw "LEGACY_TEST_CONTRACT_PATCH_FAIL"
    }

    Write-Host ""
    Write-Host "=== REAPPLY CAPTURE V2 ==="
    Write-Host "NOTE=Capture V2 owns target tests and full regression."

    $stdout = Join-Path $rollback "capture_v2_stdout.txt"
    $stderr = Join-Path $rollback "capture_v2_stderr.txt"

    $proc = Start-Process `
        -FilePath "powershell.exe" `
        -ArgumentList @(
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", "`"$CaptureV2Script`"",
            "-ProjectRoot", "`"$ProjectRoot`""
        ) `
        -Wait `
        -PassThru `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr

    $childOut = ""
    $childErr = ""

    if (Test-Path -LiteralPath $stdout) {
        $childOut = [System.IO.File]::ReadAllText($stdout)
        Write-Host $childOut
    }

    if (Test-Path -LiteralPath $stderr) {
        $childErr = [System.IO.File]::ReadAllText($stderr)
        if (-not [string]::IsNullOrWhiteSpace($childErr)) {
            Write-Host "=== CHILD STDERR ==="
            Write-Host $childErr
        }
    }

    if ($proc.ExitCode -ne 0) {
        Restore-All

        [System.IO.File]::WriteAllText(
            $report,
            @"
RESULT=CAPTURE_V2_REAPPLY_FAIL
ROLLBACK=SUCCESS
PRODUCTION_STATUS=PRE_RECOVERY_RESTORED
FAILED_NODE=$expectedNode

=== LEGACY PATCH ===
$($patchOutput -join "`n")

=== CAPTURE V2 STDOUT ===
$childOut

=== CAPTURE V2 STDERR ===
$childErr
"@
        )

        Write-Host ""
        Write-Host "=== FAILURE ==="
        Write-Host "ERROR=CAPTURE_V2_REAPPLY_FAIL"
        Write-Host "ROLLBACK=SUCCESS"
        Write-Host "PRODUCTION_STATUS=PRE_RECOVERY_RESTORED"
        Write-Host ("REPORT=" + $report)
        throw "CAPTURE_V2_LEGACY_RECOVERY_REAPPLY_FAIL"
    }

    if ($childOut -notmatch "DAILY10_FULL_RESEARCH_CAPTURE_V2=COMPLETE") {
        Restore-All
        throw "CAPTURE_V2_SUCCESS_MARKER_MISSING"
    }

    [System.IO.File]::WriteAllText(
        $report,
        @"
=== HISSE ROBOTU — CAPTURE V2 LEGACY CONTRACT RECOVERY V1 ===
RESULT=SUCCESS
EXACT_FAILED_NODE=$expectedNode
LEGACY_TEST_CONTRACT_PATCH=PASS
CAPTURE_V2_REAPPLY=PASS
TARGET_TEST=PASS
FULL_REGRESSION=PASS
RANKING_MEMORY_DATA_MUTATION=NO
FULL_RESEARCH_CAPTURE_CONTRACT=PATCHED
NEXT=REBUILD_25AUG_CANONICAL_RANKING_MEMORY_SESSION_WITH_BACKUP_AND_EXACT_PARITY

=== LEGACY PATCH ===
$($patchOutput -join "`n")

=== CAPTURE V2 OUTPUT ===
$childOut
"@
    )

    Write-Host ""
    Write-Host "=== SUCCESS ==="
    Write-Host "EXACT_LEGACY_REGRESSION_CONTRACT=REPAIRED"
    Write-Host "FULL_RESEARCH_CAPTURE_CONTRACT=PATCHED"
    Write-Host "DEDICATED_RANKING_MEMORY_ROWS=YES"
    Write-Host "RANKING_MEMORY_EXISTING_DATA=UNCHANGED"
    Write-Host "TARGET_TEST=PASS"
    Write-Host "FULL_REGRESSION=PASS"
    Write-Host "CAPTURE_V2_LEGACY_CONTRACT_RECOVERY_V1=COMPLETE"
    Write-Host "NEXT=REBUILD_25AUG_CANONICAL_RANKING_MEMORY_SESSION_WITH_BACKUP_AND_EXACT_PARITY"
    Write-Host ("REPORT=" + $report)
}
catch {
    if ($_.Exception.Message -notmatch "CAPTURE_V2_LEGACY_RECOVERY_REAPPLY_FAIL|CAPTURE_V2_SUCCESS_MARKER_MISSING|LEGACY_TEST_CONTRACT_PATCH_FAIL") {
        Restore-All
    }
    throw
}
finally {
    Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
}
