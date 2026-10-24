param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Dashboard = Join-Path $ProjectRoot "backend\dashboard.py"

foreach ($p in @($Python, $Dashboard)) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "REQUIRED_PATH_MISSING=$p"
    }
}

$oldPythonPath = $env:PYTHONPATH
$tmp = Join-Path $env:TEMP "hisse_daily10_capture_seam_ast_inspection_v2.py"

try {
    Write-Host "=== HISSE ROBOTU — CAPTURE SEAM AST INSPECTION V2 ==="
    Write-Host "MODE=READ_ONLY"
    Write-Host "PRODUCTION_MUTATION=NO"
    Write-Host "GOAL=PROVE_CURRENT_DASHBOARD_RANKING_MEMORY_ROWS_SOURCE"

    $env:PYTHONPATH = if ([string]::IsNullOrWhiteSpace($oldPythonPath)) {
        $ProjectRoot
    } else {
        "$ProjectRoot;$oldPythonPath"
    }

    $code = @'
from __future__ import annotations

import ast
import hashlib
import sys
from pathlib import Path

root = Path(sys.argv[1])
path = root / "backend" / "dashboard.py"

raw = path.read_bytes()
text = raw.decode("utf-8", errors="replace")
lines = text.splitlines()
tree = ast.parse(text)

print(f"SOURCE={path}")
print(f"SHA256={hashlib.sha256(raw).hexdigest()}")

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

def collect_assignments(fn):
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

def names_loaded(node: ast.AST):
    return sorted({
        n.id
        for n in ast.walk(node)
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
    })

def classify_expr(node: ast.AST, assignments, seen=None):
    if seen is None:
        seen = set()

    compact = unparse(node).replace(" ", "")

    if "sonuc.filtrelenmis.adaylar" in compact:
        return "FULL_FILTERED_RESEARCH"

    if "aday_tablosu_kayitlari(sonuc)" in compact:
        return "DISPLAY_HELPER"

    if "sonuc.adaylar" in compact:
        return "DISPLAY_RESULT"

    if isinstance(node, ast.Name):
        if node.id in seen:
            return "UNRESOLVED"
        values = assignments.get(node.id, [])
        if len(values) == 1:
            return classify_expr(values[0], assignments, seen | {node.id})
        if len(values) > 1:
            kinds = {
                classify_expr(value, assignments, seen | {node.id})
                for value in values
            }
            if len(kinds) == 1:
                return next(iter(kinds))
            return "MULTIPLE_ASSIGNMENTS:" + ",".join(sorted(kinds))

    return "UNRESOLVED"

def trace_name(name, assignments, depth=0, seen=None):
    if seen is None:
        seen = set()
    indent = "  " * depth

    if name in seen:
        return [f"{indent}{name} -> CYCLE"]

    values = assignments.get(name, [])
    if not values:
        return [f"{indent}{name} -> EXTERNAL_OR_PARAMETER"]

    result = []
    for idx, value in enumerate(values, start=1):
        prefix = f"{indent}{name}"
        if len(values) > 1:
            prefix += f"[{idx}]"
        result.append(f"{prefix} -> {unparse(value)}")
        if depth < 8:
            for child in names_loaded(value):
                if child in assignments and child != name:
                    result.extend(
                        trace_name(
                            child,
                            assignments,
                            depth + 1,
                            seen | {name},
                        )
                    )
    return result

obs_calls = []
append_calls = []
publisher_calls = []

for node in ast.walk(tree):
    if not isinstance(node, ast.Call):
        continue
    fn = dotted(node.func)
    if fn.endswith("observations_from_research_rows"):
        obs_calls.append(node)
    elif fn.endswith("append_snapshot"):
        append_calls.append(node)
    elif fn.endswith("write_scan_row_opinion"):
        publisher_calls.append(node)

print()
print("=== CALL INVENTORY ===")
print(f"OBSERVATIONS_FROM_RESEARCH_ROWS_CALLS={len(obs_calls)}")
print(f"APPEND_SNAPSHOT_CALLS={len(append_calls)}")
print(f"WRITE_SCAN_ROW_OPINION_CALLS={len(publisher_calls)}")

results = []

for idx, call in enumerate(sorted(obs_calls, key=lambda n: n.lineno), start=1):
    fn = enclosing_function(call)
    assignments = collect_assignments(fn)
    kwargs = {kw.arg: kw.value for kw in call.keywords if kw.arg}
    rows = kwargs.get("rows")

    print()
    print(f"=== RANKING MEMORY CALL {idx} ===")
    print(f"LINE={call.lineno}")
    print(f"FUNCTION={fn.name if fn else 'MODULE_SCOPE'}")

    if rows is None:
        print("ROWS_EXPR=MISSING")
        print("ROWS_ORIGIN_CLASS=ROWS_KEYWORD_MISSING")
        results.append("ROWS_KEYWORD_MISSING")
        continue

    print(f"ROWS_EXPR={unparse(rows)}")
    loaded = names_loaded(rows)
    print("ROWS_LOADED_NAMES=" + ",".join(loaded))

    print("DATAFLOW_TRACE_BEGIN")
    traced = False
    for name in loaded:
        if name in assignments:
            traced = True
            for line in trace_name(name, assignments):
                print(line)
    if not traced:
        print("NO_LOCAL_ASSIGNMENT_TRACE")
    print("DATAFLOW_TRACE_END")

    kind = classify_expr(rows, assignments)
    print(f"ROWS_ORIGIN_CLASS={kind}")
    results.append(kind)

    start = max(1, call.lineno - 35)
    end = min(len(lines), getattr(call, "end_lineno", call.lineno) + 35)
    print("SOURCE_WINDOW_BEGIN")
    for n in range(start, end + 1):
        print(f"{n:04d}: {lines[n-1]}")
    print("SOURCE_WINDOW_END")

print()
print("=== SHARED-ROW SIDE EFFECT CHECK ===")

# Find local names that feed ranking rows and also feed the external publisher.
ranking_names = set()
for call in obs_calls:
    kwargs = {kw.arg: kw.value for kw in call.keywords if kw.arg}
    rows = kwargs.get("rows")
    if rows is not None:
        ranking_names.update(names_loaded(rows))

publisher_names = set()
for call in publisher_calls:
    for arg in call.args:
        publisher_names.update(names_loaded(arg))
    for kw in call.keywords:
        publisher_names.update(names_loaded(kw.value))

shared = sorted(ranking_names & publisher_names)

print(
    "RANKING_ROWS_NAMES="
    + (",".join(sorted(ranking_names)) if ranking_names else "NONE")
)
print(
    "PUBLISHER_INPUT_NAMES="
    + (",".join(sorted(publisher_names)) if publisher_names else "NONE")
)
print(
    "SHARED_RANKING_AND_PUBLISHER_NAMES="
    + (",".join(shared) if shared else "NONE")
)

if shared:
    print(
        "SAFETY=DO_NOT_REPURPOSE_SHARED_ROW_VARIABLE;"
        "CREATE_DEDICATED_RANKING_MEMORY_ROWS_VARIABLE"
    )
else:
    print("SAFETY=NO_SHARED_ROW_VARIABLE_PROVEN")

print()
print("=== FINAL CAPTURE-SEAM DECISION ===")

unique = sorted(set(results))

if results and all(x == "FULL_FILTERED_RESEARCH" for x in results):
    print("CAPTURE_SEAM=ALREADY_FULL_FILTERED_RESEARCH")
    print("NEXT=DO_NOT_PATCH_CAPTURE;DIAGNOSE_EXISTING_25AUG_MEMORY_PARITY")
elif results and all(x in {"DISPLAY_HELPER", "DISPLAY_RESULT"} for x in results):
    print("CAPTURE_SEAM=PROVEN_PARTIAL_DISPLAY_DERIVED")
    if shared:
        print(
            "PATCH_SHAPE=ADD_DEDICATED_RANKING_MEMORY_ROWS_FROM_SONUC_FILTRELENMIS_ADAYLAR;"
            "DO_NOT_CHANGE_SHARED_DISPLAY_OR_PUBLISHER_ROWS"
        )
    else:
        print(
            "PATCH_SHAPE=REBIND_RANKING_MEMORY_ROWS_ONLY_TO_SONUC_FILTRELENMIS_ADAYLAR"
        )
    print(
        "NEXT=BUILD_ADAPTIVE_CAPTURE_FIX_WITH_TARGET_TEST_FULL_REGRESSION_AND_ROLLBACK"
    )
else:
    print("CAPTURE_SEAM=UNRESOLVED_OR_MIXED")
    print("ROWS_ORIGIN_CLASSES=" + ",".join(unique))
    print(
        "NEXT=DO_NOT_MUTATE;USE_PRINTED_ROWS_EXPR_TRACE_AND_SOURCE_WINDOW"
    )

print("CAPTURE_SEAM_AST_INSPECTION_V2=PASS")
'@

    [System.IO.File]::WriteAllText(
        $tmp,
        $code,
        (New-Object System.Text.UTF8Encoding($false))
    )

    & $Python $tmp $ProjectRoot
    if ($LASTEXITCODE -ne 0) {
        throw "CAPTURE_SEAM_AST_INSPECTION_V2_FAIL"
    }
}
finally {
    Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue

    if ($null -eq $oldPythonPath) {
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    } else {
        $env:PYTHONPATH = $oldPythonPath
    }
}
