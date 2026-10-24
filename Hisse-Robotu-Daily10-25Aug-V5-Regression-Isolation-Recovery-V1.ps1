param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu",
    [string]$RebuildScript = "C:\Users\user\Downloads\Hisse-Robotu-Daily10-25Aug-Canonical-Session-Rebuild-V5.ps1"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$TestFile = Join-Path $ProjectRoot "backend\tests\test_prebreakout_daily_operation.py"
$MemoryFile = Join-Path $ProjectRoot "data\ranking_memory\rank_observations.jsonl"
$Discovery = Join-Path $ProjectRoot "_discovery"

foreach ($p in @($Python, $TestFile, $MemoryFile, $RebuildScript)) {
    if (-not (Test-Path -LiteralPath $p -PathType Leaf)) {
        throw "REQUIRED_FILE_MISSING=$p"
    }
}

New-Item -ItemType Directory -Force -Path $Discovery | Out-Null

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$rollback = Join-Path $ProjectRoot ("_rollback\daily10-25aug-v5-regression-isolation-recovery-" + $stamp)
$report = Join-Path $Discovery ("Hisse-Robotu-Daily10-25Aug-V5-Regression-Isolation-Recovery-V1-" + $stamp + ".txt")
$patchPy = Join-Path $env:TEMP ("hisse_prebreakout_test_isolation_patch_" + [guid]::NewGuid().ToString("N") + ".py")

New-Item -ItemType Directory -Force -Path $rollback | Out-Null
$backupTest = Join-Path $rollback "test_prebreakout_daily_operation.py"
Copy-Item -LiteralPath $TestFile -Destination $backupTest -Force

$memoryShaBefore = (Get-FileHash -LiteralPath $MemoryFile -Algorithm SHA256).Hash
$testShaBefore = (Get-FileHash -LiteralPath $TestFile -Algorithm SHA256).Hash

$oldPythonPath = $env:PYTHONPATH
$oldPythonUtf8 = $env:PYTHONUTF8
$oldPythonIoEncoding = $env:PYTHONIOENCODING

function Restore-TestFile {
    Copy-Item -LiteralPath $backupTest -Destination $TestFile -Force
}

try {
    Write-Host "=== HISSE ROBOTU — 25AUG V5 REGRESSION ISOLATION RECOVERY V1 ==="
    Write-Host "MODE=CONTROLLED_TEST_ISOLATION_FIX_THEN_REBUILD"
    Write-Host "RANKING_LOGIC_CHANGE=NO"
    Write-Host "PREBREAKOUT_PRODUCTION_LOGIC_CHANGE=NO"
    Write-Host "TEST_ONLY_MUTATION=YES"
    Write-Host "TEST_FILE_BACKUP=YES"
    Write-Host "ROLLBACK_TEST_FILE_IF_ANY_FAILURE=YES"
    Write-Host ("MEMORY_SHA_BEFORE=" + $memoryShaBefore)
    Write-Host ("TEST_SHA_BEFORE=" + $testShaBefore)
    Write-Host ""

    $env:PYTHONPATH = if ([string]::IsNullOrWhiteSpace($oldPythonPath)) {
        $ProjectRoot
    } else {
        "$ProjectRoot;$oldPythonPath"
    }
    $env:PYTHONUTF8 = "1"
    $env:PYTHONIOENCODING = "utf-8"

    $patchCode = @'
from __future__ import annotations

import ast
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
tree = ast.parse(text, filename=str(path))

SIDE_EFFECT_KWARGS = (
    ("archive_path", 'tmp_path / "prebreakout_daily_operation_archive.jsonl"'),
    ("alarm_history_path", 'tmp_path / "prebreakout_operation_alarm_history.jsonl"'),
    ("decision_journal_path", 'tmp_path / "prebreakout_operation_decision_journal.jsonl"'),
    ("diagnosis_path", 'tmp_path / "prebreakout_operation_diagnosis.json"'),
    ("recovery_path", 'tmp_path / "prebreakout_operation_recovery.json"'),
)

targets: list[tuple[ast.Call, ast.FunctionDef]] = []

for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
    fn_args = {
        arg.arg
        for arg in (
            list(fn.args.posonlyargs)
            + list(fn.args.args)
            + list(fn.args.kwonlyargs)
        )
    }
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_target = (
            isinstance(func, ast.Attribute)
            and func.attr == "gunluk_operasyonu_guvenli_calistir"
            and isinstance(func.value, ast.Name)
            and func.value.id == "module"
        )
        if not is_target:
            continue
        if "tmp_path" not in fn_args:
            raise RuntimeError(
                f"TEST_ISOLATION_BLOCKED:{fn.name}:TARGET_CALL_WITHOUT_TMP_PATH"
            )
        targets.append((node, fn))

if not targets:
    raise RuntimeError("TEST_ISOLATION_BLOCKED:NO_DAILY_OPERATION_CALLS_FOUND")

print(f"TARGET_CALL_COUNT={len(targets)}")

patches: list[tuple[int, int, str]] = []
patched_count = 0
already_isolated_count = 0

lines = text.splitlines(keepends=True)
line_starts = []
offset = 0
for line in lines:
    line_starts.append(offset)
    offset += len(line)

def absolute_offset(lineno: int, col: int) -> int:
    return line_starts[lineno - 1] + col

for node, fn in targets:
    existing = {kw.arg for kw in node.keywords if kw.arg is not None}
    missing = [(name, expr) for name, expr in SIDE_EFFECT_KWARGS if name not in existing]

    if not missing:
        already_isolated_count += 1
        print(f"CALL={fn.name}:ALREADY_ISOLATED")
        continue

    if node.end_lineno is None or node.end_col_offset is None:
        raise RuntimeError(
            f"TEST_ISOLATION_BLOCKED:{fn.name}:NO_AST_END_POSITION"
        )

    start = absolute_offset(node.lineno, node.col_offset)
    end = absolute_offset(node.end_lineno, node.end_col_offset)
    segment = text[start:end]

    if not segment.rstrip().endswith(")"):
        raise RuntimeError(
            f"TEST_ISOLATION_BLOCKED:{fn.name}:CALL_SEGMENT_NOT_CLOSED"
        )

    closing = segment.rfind(")")
    insertion = "".join(f", {name}={expr}" for name, expr in missing)
    replacement = segment[:closing] + insertion + segment[closing:]

    patches.append((start, end, replacement))
    patched_count += 1
    print(
        f"CALL={fn.name}:PATCHED_MISSING="
        + ",".join(name for name, _ in missing)
    )

if patched_count == 0 and already_isolated_count == len(targets):
    print("TEST_ISOLATION_STATUS=ALREADY_COMPLETE")
    sys.exit(0)

for start, end, replacement in sorted(patches, reverse=True):
    text = text[:start] + replacement + text[end:]

# Contract check after patch.
patched_tree = ast.parse(text, filename=str(path))
remaining = []
for fn in [n for n in ast.walk(patched_tree) if isinstance(n, ast.FunctionDef)]:
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (
            isinstance(func, ast.Attribute)
            and func.attr == "gunluk_operasyonu_guvenli_calistir"
            and isinstance(func.value, ast.Name)
            and func.value.id == "module"
        ):
            continue
        existing = {kw.arg for kw in node.keywords if kw.arg is not None}
        missing_names = [name for name, _ in SIDE_EFFECT_KWARGS if name not in existing]
        if missing_names:
            remaining.append((fn.name, missing_names))

if remaining:
    raise RuntimeError(f"TEST_ISOLATION_BLOCKED:POSTPATCH_MISSING={remaining!r}")

compile(text, str(path), "exec")
path.write_text(text, encoding="utf-8", newline="")

print(f"PATCHED_CALL_COUNT={patched_count}")
print("PRODUCTION_SIDE_EFFECT_PATHS_IN_TEST_CALLS=TMP_PATH_SCOPED")
print("TEST_ISOLATION_PATCH=PASS")
'@

    [System.IO.File]::WriteAllText($patchPy, $patchCode, [System.Text.UTF8Encoding]::new($false))

    Write-Host "=== PATCH TEST ISOLATION ==="
    $patchOutput = & $Python $patchPy $TestFile 2>&1
    $patchExit = $LASTEXITCODE
    $patchOutput | ForEach-Object { Write-Host $_ }

    if ($patchExit -ne 0) {
        Restore-TestFile
        throw "TEST_ISOLATION_PATCH_FAIL"
    }

    $testShaPatched = (Get-FileHash -LiteralPath $TestFile -Algorithm SHA256).Hash
    Write-Host ("TEST_SHA_PATCHED=" + $testShaPatched)

    Write-Host ""
    Write-Host "=== TARGETED PREBREAKOUT DAILY OPERATION TEST FILE ==="
    $targetOutput = & $Python -m pytest -q backend/tests/test_prebreakout_daily_operation.py 2>&1
    $targetExit = $LASTEXITCODE
    $targetOutput | ForEach-Object { Write-Host $_ }

    if ($targetExit -ne 0) {
        Restore-TestFile
        [System.IO.File]::WriteAllLines(
            $report,
            @(
                "=== HISSE ROBOTU — 25AUG V5 REGRESSION ISOLATION RECOVERY V1 ===",
                "RESULT=TARGETED_PREBREAKOUT_TEST_FAIL",
                "TEST_FILE_ROLLBACK=SUCCESS",
                "RANKING_MEMORY_STATUS=UNCHANGED_PRE_REBUILD",
                ""
            ) +
            @($patchOutput | ForEach-Object { [string]$_ }) +
            @("") +
            @($targetOutput | ForEach-Object { [string]$_ })
        )
        throw "TARGETED_PREBREAKOUT_TEST_FAIL"
    }

    $memoryShaBeforeRebuild = (Get-FileHash -LiteralPath $MemoryFile -Algorithm SHA256).Hash
    if ($memoryShaBeforeRebuild -ne $memoryShaBefore) {
        Restore-TestFile
        throw "PRE_REBUILD_GUARD_FAIL:RANKING_MEMORY_CHANGED_DURING_TEST_ISOLATION_STAGE"
    }

    Write-Host ""
    Write-Host "=== RE-RUN 25AUG CANONICAL REBUILD V5 ==="
    $rebuildOutput = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $RebuildScript 2>&1
    $rebuildExit = $LASTEXITCODE
    $rebuildOutput | ForEach-Object { Write-Host $_ }

    if ($rebuildExit -ne 0) {
        Restore-TestFile
        [System.IO.File]::WriteAllLines(
            $report,
            @(
                "=== HISSE ROBOTU — 25AUG V5 REGRESSION ISOLATION RECOVERY V1 ===",
                "RESULT=REBUILD_V5_FAIL",
                "TEST_FILE_ROLLBACK=SUCCESS",
                "RANKING_MEMORY_ROLLBACK=DELEGATED_TO_V5_AND_MUST_REPORT_SUCCESS",
                ""
            ) +
            @($patchOutput | ForEach-Object { [string]$_ }) +
            @("") +
            @($targetOutput | ForEach-Object { [string]$_ }) +
            @("") +
            @($rebuildOutput | ForEach-Object { [string]$_ })
        )
        throw "REBUILD_V5_FAIL_AFTER_TEST_ISOLATION_FIX"
    }

    $memoryShaAfter = (Get-FileHash -LiteralPath $MemoryFile -Algorithm SHA256).Hash
    $testShaAfter = (Get-FileHash -LiteralPath $TestFile -Algorithm SHA256).Hash

    [System.IO.File]::WriteAllLines(
        $report,
        @(
            "=== HISSE ROBOTU — 25AUG V5 REGRESSION ISOLATION RECOVERY V1 ===",
            "RESULT=SUCCESS",
            "PREBREAKOUT_TEST_ISOLATION=PASS",
            "TARGETED_PREBREAKOUT_TEST=PASS",
            "REBUILD_V5=PASS",
            "TEST_FILE_ROLLBACK=NOT_NEEDED",
            ("MEMORY_SHA_BEFORE=" + $memoryShaBefore),
            ("MEMORY_SHA_AFTER=" + $memoryShaAfter),
            ("TEST_SHA_BEFORE=" + $testShaBefore),
            ("TEST_SHA_AFTER=" + $testShaAfter),
            "NEXT=INVENTORY_AND_NORMALIZE_18_TO_24_OPERATIONAL_CONTRACT_HISTORY",
            ""
        ) +
        @($patchOutput | ForEach-Object { [string]$_ }) +
        @("") +
        @($targetOutput | ForEach-Object { [string]$_ }) +
        @("") +
        @($rebuildOutput | ForEach-Object { [string]$_ })
    )

    Write-Host ""
    Write-Host "=== SUCCESS ==="
    Write-Host "PREBREAKOUT_TEST_ISOLATION=PASS"
    Write-Host "TARGETED_PREBREAKOUT_TEST=PASS"
    Write-Host "25AUG_CANONICAL_REBUILD_V5=PASS"
    Write-Host "TEST_FILE_ISOLATION_FIX=KEPT"
    Write-Host ("MEMORY_SHA_AFTER=" + $memoryShaAfter)
    Write-Host "NEXT=INVENTORY_AND_NORMALIZE_18_TO_24_OPERATIONAL_CONTRACT_HISTORY"
    Write-Host ("REPORT=" + $report)
}
catch {
    Write-Host ""
    Write-Host "=== RECOVERY FAILURE ==="
    Write-Host ("ERROR=" + $_.Exception.Message)
    Write-Host "TEST_FILE_STATUS=RESTORED_IF_MUTATED"
    Write-Host ("REPORT=" + $report)
    throw
}
finally {
    if (Test-Path -LiteralPath $patchPy) {
        Remove-Item -LiteralPath $patchPy -Force -ErrorAction SilentlyContinue
    }

    if ($null -eq $oldPythonPath) {
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    } else {
        $env:PYTHONPATH = $oldPythonPath
    }

    if ($null -eq $oldPythonUtf8) {
        Remove-Item Env:PYTHONUTF8 -ErrorAction SilentlyContinue
    } else {
        $env:PYTHONUTF8 = $oldPythonUtf8
    }

    if ($null -eq $oldPythonIoEncoding) {
        Remove-Item Env:PYTHONIOENCODING -ErrorAction SilentlyContinue
    } else {
        $env:PYTHONIOENCODING = $oldPythonIoEncoding
    }
}
