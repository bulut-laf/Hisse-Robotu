param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Dashboard = Join-Path $ProjectRoot "backend\dashboard.py"
$Test = Join-Path $ProjectRoot "backend\tests\test_ranking_memory_full_research_capture_v2.py"
$Discovery = Join-Path $ProjectRoot "_discovery"

foreach ($p in @($Python, $Dashboard)) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "REQUIRED_PATH_MISSING=$p"
    }
}

New-Item -ItemType Directory -Force -Path $Discovery | Out-Null

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$rollback = Join-Path $ProjectRoot "_rollback\daily10-full-research-capture-v2-$stamp"
$report = Join-Path $Discovery "Hisse-Robotu-Daily10-Full-Research-Capture-V2-$stamp.txt"
$tmp = Join-Path $env:TEMP "hisse_daily10_full_research_capture_v2_patch.py"

New-Item -ItemType Directory -Force -Path $rollback | Out-Null

$dashboardBackup = Join-Path $rollback "dashboard.py"
Copy-Item -LiteralPath $Dashboard -Destination $dashboardBackup -Force

$testExisted = Test-Path -LiteralPath $Test
if ($testExisted) {
    Copy-Item -LiteralPath $Test -Destination (Join-Path $rollback "test_ranking_memory_full_research_capture_v2.py") -Force
}

function Restore-Rollback {
    Copy-Item -LiteralPath $dashboardBackup -Destination $Dashboard -Force

    if ($testExisted) {
        Copy-Item `
            -LiteralPath (Join-Path $rollback "test_ranking_memory_full_research_capture_v2.py") `
            -Destination $Test `
            -Force
    }
    elseif (Test-Path -LiteralPath $Test) {
        Remove-Item -LiteralPath $Test -Force
    }
}

function Write-Utf8([string]$path, [string]$text) {
    [System.IO.File]::WriteAllText(
        $path,
        $text,
        (New-Object System.Text.UTF8Encoding($false))
    )
}

$oldPythonPath = $env:PYTHONPATH

try {
    Write-Host "=== HISSE ROBOTU — FULL RESEARCH RANKING MEMORY CAPTURE V2 ==="
    Write-Host "MODE=CONTROLLED_SOURCE_MUTATION"
    Write-Host "RANKING_MEMORY_DATA_MUTATION=NO"
    Write-Host "PATCH_STRATEGY=AST_ADAPTIVE"
    Write-Host "GOAL=REBIND_ONLY_RANKING_MEMORY_ROWS_TO_FULL_FILTERED_RESEARCH"
    Write-Host "DISPLAY_ROWS=UNCHANGED"
    Write-Host "OTHER_PUBLISHER_ROWS=UNCHANGED"
    Write-Host "NEW_ENGINE=NO"
    Write-Host "NEW_STORE=NO"

    $env:PYTHONPATH = if ([string]::IsNullOrWhiteSpace($oldPythonPath)) {
        $ProjectRoot
    } else {
        "$ProjectRoot;$oldPythonPath"
    }

    $patchCode = @'
from __future__ import annotations

import ast
import hashlib
import sys
from pathlib import Path

root = Path(sys.argv[1])
path = root / "backend" / "dashboard.py"

raw = path.read_bytes()
source = raw.decode("utf-8")
tree = ast.parse(source)
lines = source.splitlines(keepends=True)

def dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = dotted(node.value)
        return f"{left}.{node.attr}" if left else node.attr
    return ""

def unparse(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return ast.dump(node, include_attributes=False)

def enclosing_function(target: ast.AST):
    best = None
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        end = getattr(node, "end_lineno", node.lineno)
        if node.lineno <= target.lineno <= end:
            if best is None:
                best = node
            else:
                best_span = getattr(best, "end_lineno", best.lineno) - best.lineno
                node_span = end - node.lineno
                if node_span < best_span:
                    best = node
    return best

def assignments_for(fn):
    out = {}
    if fn is None:
        return out
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    out.setdefault(target.id, []).append(node.value)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.value is not None:
                out.setdefault(node.target.id, []).append(node.value)
    return out

def classify(node: ast.AST, assignments, seen=None):
    if seen is None:
        seen = set()

    compact = unparse(node).replace(" ", "")

    if "sonuc.filtrelenmis.adaylar" in compact:
        return "FULL_FILTERED_RESEARCH"
    if "aday_tablosu_kayitlari(sonuc)" in compact:
        return "PARTIAL_DISPLAY"
    if "sonuc.adaylar" in compact:
        return "PARTIAL_DISPLAY"

    if isinstance(node, ast.Name):
        if node.id in seen:
            return "UNRESOLVED"
        values = assignments.get(node.id, ())
        if len(values) == 1:
            return classify(values[0], assignments, seen | {node.id})
        if len(values) > 1:
            kinds = {classify(v, assignments, seen | {node.id}) for v in values}
            if len(kinds) == 1:
                return next(iter(kinds))

    return "UNRESOLVED"

calls = []
for node in ast.walk(tree):
    if not isinstance(node, ast.Call):
        continue
    if dotted(node.func).endswith("observations_from_research_rows"):
        fn = enclosing_function(node)
        assignments = assignments_for(fn)
        kwargs = {kw.arg: kw.value for kw in node.keywords if kw.arg}
        rows = kwargs.get("rows")
        if rows is None:
            continue
        calls.append((node, rows, fn, assignments, classify(rows, assignments)))

partial = [item for item in calls if item[4] == "PARTIAL_DISPLAY"]
full = [item for item in calls if item[4] == "FULL_FILTERED_RESEARCH"]
unresolved = [item for item in calls if item[4] == "UNRESOLVED"]

print(f"OBSERVATION_CALL_COUNT={len(calls)}")
print(f"PARTIAL_CALL_COUNT={len(partial)}")
print(f"FULL_CALL_COUNT={len(full)}")
print(f"UNRESOLVED_CALL_COUNT={len(unresolved)}")

if full and not partial and not unresolved:
    print("PATCH_RESULT=ALREADY_FULL_FILTERED_RESEARCH")
    raise SystemExit(20)

if len(partial) != 1 or full or unresolved:
    raise RuntimeError(
        "FAIL-CLOSED:EXPECTED_EXACTLY_ONE_PARTIAL_RANKING_MEMORY_CALL;"
        f"partial={len(partial)} full={len(full)} unresolved={len(unresolved)}"
    )

call, rows_node, fn, assignments, _kind = partial[0]

if fn is None:
    raise RuntimeError("FAIL-CLOSED:RANKING_MEMORY_CALL_NOT_INSIDE_FUNCTION")

# Find the rows keyword itself.
rows_kw = next(
    kw for kw in call.keywords
    if kw.arg == "rows"
)

# Compute an insertion point at the beginning of the statement containing
# the observations_from_research_rows call.
stmt = None
for node in ast.walk(fn):
    if not isinstance(node, ast.stmt):
        continue
    end = getattr(node, "end_lineno", node.lineno)
    if node.lineno <= call.lineno <= end:
        if stmt is None:
            stmt = node
        else:
            old_span = getattr(stmt, "end_lineno", stmt.lineno) - stmt.lineno
            new_span = end - node.lineno
            if new_span < old_span:
                stmt = node

if stmt is None:
    raise RuntimeError("FAIL-CLOSED:ENCLOSING_STATEMENT_NOT_FOUND")

statement_line = lines[stmt.lineno - 1]
indent = statement_line[: len(statement_line) - len(statement_line.lstrip(" \t"))]

dedicated_name = "_ranking_memory_rows"

# Avoid accidental pre-existing binding ambiguity.
preexisting = []
for node in ast.walk(fn):
    if isinstance(node, ast.Name) and node.id == dedicated_name:
        preexisting.append(node)

if preexisting:
    raise RuntimeError(
        f"FAIL-CLOSED:{dedicated_name}_ALREADY_EXISTS"
    )

block = (
    f"{indent}{dedicated_name} = tuple(\n"
    f"{indent}    {{\n"
    f'{indent}        "Sıra": _rank,\n'
    f'{indent}        "Hisse": _candidate.sembol.removesuffix(".IS"),\n'
    f"{indent}    }}\n"
    f"{indent}    for _rank, _candidate in enumerate(\n"
    f"{indent}        sonuc.filtrelenmis.adaylar,\n"
    f"{indent}        start=1,\n"
    f"{indent}    )\n"
    f"{indent})\n"
)

def char_index(line_no: int, utf8_col: int) -> int:
    prefix = "".join(lines[: line_no - 1])
    line = lines[line_no - 1]
    b = line.encode("utf-8")
    chars = b[:utf8_col].decode("utf-8")
    return len(prefix) + len(chars)

start = char_index(rows_node.lineno, rows_node.col_offset)
end = char_index(rows_node.end_lineno, rows_node.end_col_offset)

patched = source[:start] + dedicated_name + source[end:]

# Insertion is before statement start, but replacement above may have shifted
# offsets if rows value is earlier than the statement start (it cannot be).
insert_at = len("".join(lines[: stmt.lineno - 1]))

# Recompute insert index after replacement safely: rows is always inside stmt,
# so insertion point is before replacement and remains unchanged.
patched = patched[:insert_at] + block + patched[insert_at:]

# Parse the result before writing.
new_tree = ast.parse(patched)

# Contract proof after patch.
new_calls = []
for node in ast.walk(new_tree):
    if isinstance(node, ast.Call) and dotted(node.func).endswith(
        "observations_from_research_rows"
    ):
        kwargs = {kw.arg: kw.value for kw in node.keywords if kw.arg}
        rows = kwargs.get("rows")
        if rows is not None:
            new_calls.append(rows)

if len(new_calls) != len(calls):
    raise RuntimeError("FAIL-CLOSED:OBSERVATION_CALL_COUNT_CHANGED")

if not any(
    isinstance(rows, ast.Name) and rows.id == dedicated_name
    for rows in new_calls
):
    raise RuntimeError("FAIL-CLOSED:DEDICATED_ROWS_BINDING_NOT_INSTALLED")

if "sonuc.filtrelenmis.adaylar" not in patched:
    raise RuntimeError("FAIL-CLOSED:FULL_FILTERED_SOURCE_MISSING_AFTER_PATCH")

path.write_text(patched, encoding="utf-8", newline="")

print(f"PATCHED_FILE={path}")
print(f"SHA_BEFORE={hashlib.sha256(raw).hexdigest()}")
print(f"SHA_AFTER={hashlib.sha256(path.read_bytes()).hexdigest()}")
print(f"PATCHED_CALL_LINE={call.lineno}")
print(f"OLD_ROWS_EXPR={unparse(rows_node)}")
print(f"NEW_ROWS_EXPR={dedicated_name}")
print("DEDICATED_SOURCE=sonuc.filtrelenmis.adaylar")
print("PATCH_RESULT=PASS")
'@

    [System.IO.File]::WriteAllText(
        $tmp,
        $patchCode,
        (New-Object System.Text.UTF8Encoding($false))
    )

    Write-Host ""
    Write-Host "=== ADAPTIVE PATCH ==="

    $patchOutput = & $Python $tmp $ProjectRoot 2>&1
    $patchExit = $LASTEXITCODE
    $patchOutput | ForEach-Object { Write-Host $_ }

    if ($patchExit -eq 20) {
        Restore-Rollback
        Write-Host ""
        Write-Host "=== STOP ==="
        Write-Host "CAPTURE_CONTRACT=ALREADY_FULL_FILTERED_RESEARCH"
        Write-Host "MUTATION=NOT_NEEDED"
        Write-Host "ROLLBACK=SUCCESS"
        throw "CAPTURE_ALREADY_FULL_FILTERED_RESEARCH"
    }

    if ($patchExit -ne 0) {
        Restore-Rollback
        Write-Host ""
        Write-Host "=== FAILURE ==="
        Write-Host "ERROR=ADAPTIVE_PATCH_FAIL"
        Write-Host "ROLLBACK=SUCCESS"
        Write-Host "PRODUCTION_STATUS=PRE_PATCH_RESTORED"
        throw "FULL_RESEARCH_CAPTURE_V2_PATCH_FAIL"
    }

    $testText = @'
from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = ROOT / "backend" / "dashboard.py"
MARKET_SCANNER = ROOT / "backend" / "app" / "analysis" / "market_scanner.py"


def _dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = _dotted(node.value)
        return f"{left}.{node.attr}" if left else node.attr
    return ""


def test_ranking_memory_uses_dedicated_full_filtered_rows():
    source = DASHBOARD.read_text(encoding="utf-8")
    tree = ast.parse(source)

    dedicated = []
    observation_rows = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if any(
                isinstance(target, ast.Name)
                and target.id == "_ranking_memory_rows"
                for target in node.targets
            ):
                dedicated.append(node.value)

        if isinstance(node, ast.Call) and _dotted(node.func).endswith(
            "observations_from_research_rows"
        ):
            kwargs = {kw.arg: kw.value for kw in node.keywords if kw.arg}
            if "rows" in kwargs:
                observation_rows.append(kwargs["rows"])

    assert len(dedicated) == 1
    expr = ast.unparse(dedicated[0]).replace(" ", "")
    assert "sonuc.filtrelenmis.adaylar" in expr
    assert "sonuc.adaylar" not in expr
    assert "aday_tablosu_kayitlari(sonuc)" not in expr

    assert any(
        isinstance(rows, ast.Name)
        and rows.id == "_ranking_memory_rows"
        for rows in observation_rows
    )


def test_display_candidate_limit_contract_remains_unchanged():
    source = MARKET_SCANNER.read_text(encoding="utf-8")
    compact = source.replace(" ", "").replace("\n", "")

    assert "filtrelenmis.adaylar[:istek.maksimum_aday]" in compact


def test_patch_does_not_repurpose_existing_shared_rows():
    source = DASHBOARD.read_text(encoding="utf-8")

    # Existing display / three-system rows may continue to exist.
    # Ranking Memory must use its own dedicated row source.
    assert "_ranking_memory_rows" in source
    assert "rows=_ranking_memory_rows" in source.replace(" ", "")
'@

    Write-Utf8 $Test $testText

    Set-Location $ProjectRoot

    Write-Host ""
    Write-Host "=== TARGET TESTS ==="

    $targetArgs = @(
        "-m", "pytest", "-q",
        "backend/tests/test_ranking_memory_full_research_capture_v2.py"
    )

    if (Test-Path -LiteralPath (Join-Path $ProjectRoot "backend\tests\test_daily_early_trajectory_v1.py")) {
        $targetArgs += "backend/tests/test_daily_early_trajectory_v1.py"
    }

    if (Test-Path -LiteralPath (Join-Path $ProjectRoot "backend\tests\test_historical_research_replay_v1.py")) {
        $targetArgs += "backend/tests/test_historical_research_replay_v1.py"
    }

    $targetOutput = & $Python @targetArgs 2>&1
    $targetExit = $LASTEXITCODE
    $targetOutput | ForEach-Object { Write-Host $_ }

    if ($targetExit -ne 0) {
        Restore-Rollback

        [System.IO.File]::WriteAllLines(
            $report,
            @(
                "RESULT=TARGET_TEST_FAIL",
                "ROLLBACK=SUCCESS",
                "PRODUCTION_STATUS=PRE_PATCH_RESTORED",
                ""
            ) +
            @($patchOutput | ForEach-Object { [string]$_ }) +
            @("") +
            @($targetOutput | ForEach-Object { [string]$_ })
        )

        Write-Host ""
        Write-Host "=== FAILURE ==="
        Write-Host "ERROR=TARGET_TEST_FAIL"
        Write-Host "ROLLBACK=SUCCESS"
        Write-Host "PRODUCTION_STATUS=PRE_PATCH_RESTORED"
        Write-Host ("REPORT=" + $report)
        throw "FULL_RESEARCH_CAPTURE_V2_TARGET_TEST_FAIL"
    }

    Write-Host ""
    Write-Host "=== FULL REGRESSION ==="

    $regOutput = & $Python -m pytest -q 2>&1
    $regExit = $LASTEXITCODE
    $regOutput | ForEach-Object { Write-Host $_ }

    if ($regExit -ne 0) {
        Restore-Rollback

        [System.IO.File]::WriteAllLines(
            $report,
            @(
                "RESULT=FULL_REGRESSION_FAIL",
                "ROLLBACK=SUCCESS",
                "PRODUCTION_STATUS=PRE_PATCH_RESTORED",
                ""
            ) +
            @($patchOutput | ForEach-Object { [string]$_ }) +
            @("") +
            @($targetOutput | ForEach-Object { [string]$_ }) +
            @("") +
            @($regOutput | ForEach-Object { [string]$_ })
        )

        Write-Host ""
        Write-Host "=== FAILURE ==="
        Write-Host "ERROR=FULL_REGRESSION_FAIL"
        Write-Host "ROLLBACK=SUCCESS"
        Write-Host "PRODUCTION_STATUS=PRE_PATCH_RESTORED"
        Write-Host ("REPORT=" + $report)
        throw "FULL_RESEARCH_CAPTURE_V2_FULL_REGRESSION_FAIL"
    }

    [System.IO.File]::WriteAllLines(
        $report,
        @(
            "=== HISSE ROBOTU — FULL RESEARCH RANKING MEMORY CAPTURE V2 ===",
            "RESULT=SUCCESS",
            "PATCH_STRATEGY=AST_ADAPTIVE",
            "RANKING_MEMORY_DATA_MUTATION=NO",
            "DISPLAY_ROWS=UNCHANGED",
            "OTHER_PUBLISHER_ROWS=UNCHANGED",
            "CAPTURE_SOURCE=sonuc.filtrelenmis.adaylar",
            "TARGET_TEST=PASS",
            "FULL_REGRESSION=PASS",
            "NEXT=REBUILD_25AUG_CANONICAL_RANKING_MEMORY_SESSION_WITH_BACKUP_AND_EXACT_PARITY",
            ""
        ) +
        @($patchOutput | ForEach-Object { [string]$_ }) +
        @("") +
        @($targetOutput | ForEach-Object { [string]$_ }) +
        @("") +
        @($regOutput | ForEach-Object { [string]$_ })
    )

    Write-Host ""
    Write-Host "=== SUCCESS ==="
    Write-Host "FULL_RESEARCH_CAPTURE_CONTRACT=PATCHED"
    Write-Host "DEDICATED_RANKING_MEMORY_ROWS=YES"
    Write-Host "DISPLAY_ROWS=UNCHANGED"
    Write-Host "OTHER_PUBLISHER_ROWS=UNCHANGED"
    Write-Host "RANKING_MEMORY_EXISTING_DATA=UNCHANGED"
    Write-Host "TARGET_TEST=PASS"
    Write-Host "FULL_REGRESSION=PASS"
    Write-Host "DAILY10_FULL_RESEARCH_CAPTURE_V2=COMPLETE"
    Write-Host "NEXT=REBUILD_25AUG_CANONICAL_RANKING_MEMORY_SESSION_WITH_BACKUP_AND_EXACT_PARITY"
    Write-Host ("REPORT=" + $report)
}
catch {
    if ($_.Exception.Message -notmatch "FULL_RESEARCH_CAPTURE_V2_TARGET_TEST_FAIL|FULL_RESEARCH_CAPTURE_V2_FULL_REGRESSION_FAIL|FULL_RESEARCH_CAPTURE_V2_PATCH_FAIL|CAPTURE_ALREADY_FULL_FILTERED_RESEARCH") {
        Restore-Rollback
        Write-Host "ROLLBACK=SUCCESS"
        Write-Host "PRODUCTION_STATUS=PRE_PATCH_RESTORED"
    }
    throw
}
finally {
    Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue

    if ($null -eq $oldPythonPath) {
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    } else {
        $env:PYTHONPATH = $oldPythonPath
    }
}
