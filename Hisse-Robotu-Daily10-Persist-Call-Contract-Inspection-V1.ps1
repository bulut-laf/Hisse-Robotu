param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "REQUIRED_PATH_MISSING=$Python"
}

$oldPythonPath = $env:PYTHONPATH
$tmp = Join-Path $env:TEMP "hisse_daily10_persist_call_contract_inspection_v1.py"

try {
    Write-Host "=== HISSE ROBOTU — PERSIST CALL CONTRACT INSPECTION V1 ==="
    Write-Host "MODE=READ_ONLY"
    Write-Host "PRODUCTION_MUTATION=NO"
    Write-Host "GOAL=TRACE_EXACT_PRODUCTION_PERSIST_ROWS_CONTRACT"

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

skip_dirs = {
    ".git", ".venv", "node_modules", "__pycache__",
    ".pytest_cache", "_rollback",
}

def iter_py_files(base: Path):
    for path in base.rglob("*.py"):
        if any(part in skip_dirs for part in path.parts):
            continue
        yield path

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

def enclosing_function(tree: ast.AST, target: ast.AST):
    best = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
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
                    out[target.id] = node.value
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.value is not None:
                out[node.target.id] = node.value
    return out

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

def classify_expr(node, assignments, seen=None):
    if seen is None:
        seen = set()

    compact = unparse(node).replace(" ", "")

    if "filtrelenmis.adaylar[:istek.maksimum_aday]" in compact:
        return "DISPLAY_SLICE"
    if "filtered.adaylar[:request.maximum_candidates]" in compact:
        return "DISPLAY_SLICE"

    if "filtrelenmis.adaylar" in compact and "[:istek.maksimum_aday]" not in compact:
        return "FULL_FILTERED_RESEARCH"
    if "filtered.adaylar" in compact and "[:request.maximum_candidates]" not in compact:
        return "FULL_FILTERED_RESEARCH"

    if isinstance(node, ast.Name):
        if node.id in seen:
            return "UNRESOLVED"
        assigned = assignments.get(node.id)
        if assigned is None:
            return "UNRESOLVED"
        return classify_expr(assigned, assignments, seen | {node.id})

    enums = enumerate_sources(node)
    if len(enums) == 1:
        kind = classify_expr(enums[0], assignments, seen)
        if kind != "UNRESOLVED":
            return kind

    for child in ast.walk(node):
        if isinstance(child, ast.comprehension):
            kind = classify_expr(child.iter, assignments, seen)
            if kind != "UNRESOLVED":
                return kind

    return "UNRESOLVED"

def trace_name(name, assignments, depth=0, seen=None):
    if seen is None:
        seen = set()
    indent = "  " * depth

    if name in seen:
        return [f"{indent}{name} -> CYCLE"]

    expr = assignments.get(name)
    if expr is None:
        return [f"{indent}{name} -> EXTERNAL_OR_PARAMETER"]

    lines = [f"{indent}{name} -> {unparse(expr)}"]

    if depth >= 8:
        lines.append(f"{indent}  MAX_DEPTH")
        return lines

    for child_name in names_loaded(expr):
        if child_name in assignments and child_name != name:
            lines.extend(
                trace_name(
                    child_name,
                    assignments,
                    depth + 1,
                    seen | {name},
                )
            )

    return lines

calls = []

for path in iter_py_files(root):
    rel = str(path.relative_to(root))

    if rel.startswith("backend/tests/"):
        continue

    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="replace")
        tree = ast.parse(text)
    except (OSError, SyntaxError):
        continue

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not dotted(node.func).endswith("persist_research_rank_snapshot"):
            continue

        fn = enclosing_function(tree, node)
        assignments = collect_assignments(fn)
        kw = {item.arg: item.value for item in node.keywords if item.arg}
        rows = kw.get("rows")

        calls.append(
            {
                "path": path,
                "rel": rel,
                "sha": hashlib.sha256(raw).hexdigest(),
                "text": text,
                "tree": tree,
                "call": node,
                "fn": fn,
                "assignments": assignments,
                "rows": rows,
                "source": kw.get("universe_source"),
                "profile": kw.get("profile_name"),
                "asof": kw.get("as_of"),
            }
        )

print()
print("=== PRODUCTION PERSIST CALL INVENTORY ===")
print(f"CALL_COUNT={len(calls)}")

if not calls:
    print("PERSIST_CALL=NONE")
    print()
    print("=== FINAL PERSIST CONTRACT DECISION ===")
    print("PERSIST_CALL_CONTRACT=NO_CURRENT_PRODUCTION_CALL")
    print("NEXT=STOP_AND_RECHECK_WRITE_LINEAGE_RESULT")
    print("PERSIST_CALL_CONTRACT_INSPECTION_V1=PASS")
    raise SystemExit(0)

results = []

for idx, item in enumerate(
    sorted(calls, key=lambda x: (x["rel"], x["call"].lineno)),
    start=1,
):
    call = item["call"]
    rows = item["rows"]
    fn = item["fn"]
    assignments = item["assignments"]
    text_lines = item["text"].splitlines()

    print()
    print(f"=== CALL {idx} ===")
    print(f"FILE={item['rel']}")
    print(f"SHA256={item['sha']}")
    print(f"LINE={call.lineno}")
    print(f"FUNCTION={fn.name if fn else 'MODULE_SCOPE'}")

    if rows is None:
        kind = "ROWS_KEYWORD_MISSING"
        print("ROWS_EXPR=MISSING")
        print("ROWS_ORIGIN_CLASS=ROWS_KEYWORD_MISSING")
        results.append(kind)
        continue

    print(f"ROWS_EXPR={unparse(rows)}")

    enums = enumerate_sources(rows)
    if enums:
        for j, src in enumerate(enums, start=1):
            print(f"ENUMERATE_SOURCE_{j}={unparse(src)}")
    else:
        print("ENUMERATE_SOURCE=NONE")

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

    print(
        "AS_OF_EXPR="
        + (unparse(item["asof"]) if item["asof"] is not None else "-")
    )
    print(
        "UNIVERSE_SOURCE_EXPR="
        + (unparse(item["source"]) if item["source"] is not None else "-")
    )
    print(
        "PROFILE_NAME_EXPR="
        + (unparse(item["profile"]) if item["profile"] is not None else "-")
    )

    start = max(1, call.lineno - 14)
    end = min(len(text_lines), getattr(call, "end_lineno", call.lineno) + 10)

    print("SOURCE_WINDOW_BEGIN")
    for n in range(start, end + 1):
        print(f"{n:04d}: {text_lines[n-1]}")
    print("SOURCE_WINDOW_END")

print()
print("=== FINAL PERSIST CONTRACT DECISION ===")

unique = sorted(set(results))

if results and all(x == "DISPLAY_SLICE" for x in results):
    print("PERSIST_CALL_CONTRACT=PROVEN_DISPLAY_SLICE")
    print("ROOT_CAUSE=AUTHORITATIVE_PRODUCTION_PERSIST_CALL_USES_DISPLAY_SLICE")
    print(
        "NEXT=PATCH_EXACT_PROVEN_CALL_TO_FULL_FILTERED_RESEARCH;"
        "ADD_TARGET_REGRESSION;"
        "FULL_REGRESSION;"
        "THEN_REBUILD_CURRENT_CANONICAL_SNAPSHOT_BEFORE_HISTORICAL_BACKFILL"
    )
elif results and all(x == "FULL_FILTERED_RESEARCH" for x in results):
    print("PERSIST_CALL_CONTRACT=PROVEN_FULL_FILTERED_RESEARCH")
    print("ROOT_CAUSE=NOT_CURRENT_PERSIST_ROWS_SOURCE")
    print(
        "NEXT=DIAGNOSE_EXISTING_25AUG_MEMORY_PARITY_AND_HISTORICAL_WRITER_VERSION"
    )
else:
    print("PERSIST_CALL_CONTRACT=MIXED_OR_UNRESOLVED")
    print("ROWS_ORIGIN_CLASSES=" + ",".join(unique))
    print(
        "NEXT=DO_NOT_MUTATE;USE_PRINTED_FILE_LINE_ROWS_EXPR_AND_TRACE_AS_EXACT_PATCH_INPUT"
    )

print("PERSIST_CALL_CONTRACT_INSPECTION_V1=PASS")
'@

    [System.IO.File]::WriteAllText(
        $tmp,
        $code,
        (New-Object System.Text.UTF8Encoding($false))
    )

    & $Python $tmp $ProjectRoot
    if ($LASTEXITCODE -ne 0) {
        throw "PERSIST_CALL_CONTRACT_INSPECTION_V1_FAIL"
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
