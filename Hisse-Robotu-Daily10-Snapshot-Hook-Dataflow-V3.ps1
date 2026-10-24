param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$MarketScanner = Join-Path $ProjectRoot "backend\app\analysis\market_scanner.py"

foreach ($p in @($Python, $MarketScanner)) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "REQUIRED_PATH_MISSING=$p"
    }
}

$oldPythonPath = $env:PYTHONPATH
$tmp = Join-Path $env:TEMP "hisse_daily10_snapshot_hook_dataflow_v3.py"

try {
    Write-Host "=== HISSE ROBOTU — SNAPSHOT HOOK DATAFLOW INSPECTION V3 ==="
    Write-Host "MODE=READ_ONLY"
    Write-Host "PRODUCTION_MUTATION=NO"
    Write-Host "GOAL=TRACE_ROWS_EXPRESSION_TO_ORIGIN"

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
path = root / "backend/app/analysis/market_scanner.py"

raw = path.read_bytes()
text = raw.decode("utf-8", errors="replace")
lines = text.splitlines()
tree = ast.parse(text)

print(f"SOURCE={path}")
print(f"SHA256={hashlib.sha256(raw).hexdigest()}")

def unparse(node):
    try:
        return ast.unparse(node)
    except Exception:
        return ast.dump(node, include_attributes=False)

def dotted(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = dotted(node.value)
        return f"{left}.{node.attr}" if left else node.attr
    return ""

# Find BistMarketScannerService.calistir specifically.
target_fn = None
for node in tree.body:
    if isinstance(node, ast.ClassDef) and node.name == "BistMarketScannerService":
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == "calistir":
                target_fn = child
                break

if target_fn is None:
    raise RuntimeError("CALISTIR_FUNCTION_NOT_FOUND")

assignments = {}

for node in ast.walk(target_fn):
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                assignments[target.id] = node.value
    elif isinstance(node, ast.AnnAssign):
        if isinstance(node.target, ast.Name) and node.value is not None:
            assignments[node.target.id] = node.value

calls = []
for node in ast.walk(target_fn):
    if isinstance(node, ast.Call) and dotted(node.func).endswith("persist_research_rank_snapshot"):
        calls.append(node)

print()
print("=== CALISTIR ASSIGNMENTS OF INTEREST ===")
for name in sorted(assignments):
    expr = unparse(assignments[name])
    if (
        "aday" in name.lower()
        or "filtre" in name.lower()
        or "snapshot" in name.lower()
        or "rank" in name.lower()
    ):
        print(f"{name} = {expr}")

def names_loaded(node):
    return sorted({
        n.id for n in ast.walk(node)
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
    })

def enumerate_sources(node):
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Call) and dotted(n.func) == "enumerate" and n.args:
            out.append(n.args[0])
    return out

def trace_name(name, depth=0, seen=None):
    if seen is None:
        seen = set()
    indent = "  " * depth
    if name in seen:
        return [f"{indent}{name} -> CYCLE"]
    seen = set(seen)
    seen.add(name)

    expr = assignments.get(name)
    if expr is None:
        return [f"{indent}{name} -> EXTERNAL_OR_PARAMETER"]

    lines_out = [f"{indent}{name} -> {unparse(expr)}"]

    if depth >= 8:
        return lines_out + [f"{indent}  MAX_DEPTH"]

    for child_name in names_loaded(expr):
        if child_name in assignments and child_name != name:
            lines_out.extend(trace_name(child_name, depth + 1, seen))
    return lines_out

print()
print("=== SNAPSHOT CALLS ===")
if not calls:
    print("SNAPSHOT_CALL=NONE")
    print()
    print("=== FINAL DATAFLOW DECISION ===")
    print("SNAPSHOT_HOOK_DATAFLOW=NO_CALL_FOUND")
    print("NEXT=DO_NOT_MUTATE")
    print("SNAPSHOT_HOOK_DATAFLOW_V3=PASS")
    raise SystemExit(0)

decisions = []

for idx, call in enumerate(sorted(calls, key=lambda x: x.lineno), start=1):
    kw = {k.arg: k.value for k in call.keywords if k.arg}
    rows = kw.get("rows")

    print(f"CALL={idx} LINE={call.lineno}")

    if rows is None:
        print("ROWS_EXPR=MISSING")
        decisions.append("UNRESOLVED")
        continue

    rows_expr = unparse(rows)
    print(f"ROWS_EXPR={rows_expr}")

    loaded = names_loaded(rows)
    print("ROWS_LOADED_NAMES=" + ",".join(loaded))

    sources = enumerate_sources(rows)
    if not sources:
        print("ENUMERATE_SOURCE=NONE")
    else:
        for j, src in enumerate(sources, start=1):
            print(f"ENUMERATE_SOURCE_{j}={unparse(src)}")

    print("DATAFLOW_TRACE_BEGIN")
    traced_any = False
    for name in loaded:
        if name in assignments:
            traced_any = True
            for line in trace_name(name):
                print(line)
    if not traced_any:
        print("NO_LOCAL_ASSIGNMENT_TRACE")
    print("DATAFLOW_TRACE_END")

    # Classification with recursive provenance.
    def expr_kind(node, seen=None):
        if seen is None:
            seen = set()

        s = unparse(node).replace(" ", "")

        if "filtrelenmis.adaylar[:istek.maksimum_aday]" in s:
            return "DISPLAY_SLICE"
        if "filtrelenmis.adaylar" in s and "[:istek.maksimum_aday]" not in s:
            return "FULL_FILTERED"

        if isinstance(node, ast.Name):
            if node.id in seen:
                return "UNRESOLVED"
            seen = set(seen)
            seen.add(node.id)
            assigned = assignments.get(node.id)
            if assigned is None:
                return "UNRESOLVED"
            return expr_kind(assigned, seen)

        # If enumerate has one source, classify that.
        enum_srcs = enumerate_sources(node)
        if len(enum_srcs) == 1:
            return expr_kind(enum_srcs[0], seen)

        # If generator/list comprehension iterates a named local, trace it.
        for comp in ast.walk(node):
            if isinstance(comp, ast.comprehension):
                kind = expr_kind(comp.iter, seen)
                if kind != "UNRESOLVED":
                    return kind

        return "UNRESOLVED"

    kind = expr_kind(rows)
    print(f"ROWS_ORIGIN_CLASS={kind}")
    decisions.append(kind)

    start = max(1, call.lineno - 10)
    end = min(len(lines), getattr(call, "end_lineno", call.lineno) + 8)
    print("SOURCE_WINDOW_BEGIN")
    for n in range(start, end + 1):
        print(f"{n:04d}: {lines[n-1]}")
    print("SOURCE_WINDOW_END")
    print()

print("=== FINAL DATAFLOW DECISION ===")

if decisions and all(x == "DISPLAY_SLICE" for x in decisions):
    print("SNAPSHOT_HOOK_DATAFLOW=PROVEN_DISPLAY_SLICE")
    print("ROOT_CAUSE=CURRENT_SNAPSHOT_HOOK_PERSISTS_DISPLAY_SLICE")
    print("NEXT=PATCH_HOOK_TO_FULL_FILTERED_RESEARCH_WITH_TARGET_TEST_AND_FULL_REGRESSION")
elif decisions and all(x == "FULL_FILTERED" for x in decisions):
    print("SNAPSHOT_HOOK_DATAFLOW=PROVEN_FULL_FILTERED_RESEARCH")
    print("ROOT_CAUSE=NOT_CAPTURE_SLICE")
    print("NEXT=DIAGNOSE_25AUG_PARITY_CONTRACT_FROM_BACKFILL_REPORT")
else:
    print("SNAPSHOT_HOOK_DATAFLOW=UNRESOLVED")
    print("EXACT_ROWS_ORIGIN_CLASSES=" + ",".join(decisions))
    print("NEXT=USE_ROWS_EXPR_AND_DATAFLOW_TRACE_AS_PATCH_INPUT;DO_NOT_MUTATE")

print("SNAPSHOT_HOOK_DATAFLOW_V3=PASS")
'@

    [System.IO.File]::WriteAllText(
        $tmp,
        $code,
        (New-Object System.Text.UTF8Encoding($false))
    )

    & $Python $tmp $ProjectRoot
    if ($LASTEXITCODE -ne 0) {
        throw "SNAPSHOT_HOOK_DATAFLOW_V3_FAIL"
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
