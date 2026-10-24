param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu",
    [string]$ReportPath = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$MarketScanner = Join-Path $ProjectRoot "backend\app\analysis\market_scanner.py"
$MemoryFile = Join-Path $ProjectRoot "data\ranking_memory\rank_observations.jsonl"
$Discovery = Join-Path $ProjectRoot "_discovery"

foreach ($p in @($Python, $MarketScanner, $MemoryFile)) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "REQUIRED_PATH_MISSING=$p"
    }
}

if ([string]::IsNullOrWhiteSpace($ReportPath)) {
    $candidate = Get-ChildItem -LiteralPath $Discovery `
        -Filter "Hisse-Robotu-Daily10-Ranking-Memory-Backfill-V1-*.txt" `
        -File `
        | Sort-Object LastWriteTime -Descending `
        | Select-Object -First 1

    if ($null -ne $candidate) {
        $ReportPath = $candidate.FullName
    }
}

$oldPythonPath = $env:PYTHONPATH
$tmp = Join-Path $env:TEMP "hisse_daily10_snapshot_hook_contract_inspection_v2.py"

try {
    Write-Host "=== HISSE ROBOTU — SNAPSHOT HOOK CONTRACT INSPECTION V2 ==="
    Write-Host "MODE=READ_ONLY"
    Write-Host "PRODUCTION_MUTATION=NO"
    Write-Host "GOAL=PROVE_EXACT_CURRENT_RANKING_SNAPSHOT_ROWS_SOURCE"
    if (-not [string]::IsNullOrWhiteSpace($ReportPath)) {
        Write-Host ("BACKFILL_REPORT=" + $ReportPath)
    } else {
        Write-Host "BACKFILL_REPORT=NOT_FOUND"
    }

    $env:PYTHONPATH = if ([string]::IsNullOrWhiteSpace($oldPythonPath)) {
        $ProjectRoot
    } else {
        "$ProjectRoot;$oldPythonPath"
    }

    $code = @'
from __future__ import annotations

import ast
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

root = Path(sys.argv[1])
report_arg = sys.argv[2] if len(sys.argv) > 2 else ""

market_path = root / "backend/app/analysis/market_scanner.py"
memory_path = root / "data/ranking_memory/rank_observations.jsonl"

source = market_path.read_text(encoding="utf-8", errors="replace")
lines = source.splitlines()
tree = ast.parse(source)

print()
print("=== CURRENT SOURCE WINDOWS ===")

needle_lines = [
    i + 1
    for i, line in enumerate(lines)
    if "persist_research_rank_snapshot" in line
    or "adaylar = tuple" in line
    or "filtrelenmis.adaylar" in line
]

seen_windows = set()
for line_no in needle_lines:
    start = max(1, line_no - 7)
    end = min(len(lines), line_no + 14)
    key = (start, end)
    if key in seen_windows:
        continue
    seen_windows.add(key)
    print(f"--- {market_path.name}:{start}-{end} ---")
    for n in range(start, end + 1):
        print(f"{n:04d}: {lines[n-1]}")
    print()

def dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = dotted_name(node.value)
        return f"{left}.{node.attr}" if left else node.attr
    return ""

def expr_label(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return ast.dump(node, include_attributes=False)

# Find assignment of local name `adaylar`
adaylar_assignments = []
for node in ast.walk(tree):
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        targets = []
        value = None
        if isinstance(node, ast.Assign):
            targets = node.targets
            value = node.value
        else:
            targets = [node.target]
            value = node.value
        if value is None:
            continue
        if any(isinstance(t, ast.Name) and t.id == "adaylar" for t in targets):
            adaylar_assignments.append((node.lineno, value))

print("=== AST: ADAYLAR ASSIGNMENT ===")
if not adaylar_assignments:
    print("ADAYLAR_ASSIGNMENT=NONE")
else:
    for lineno, value in adaylar_assignments:
        print(f"LINE={lineno} EXPR={expr_label(value)}")

# Locate snapshot calls and classify rows keyword.
snapshot_calls = []
for node in ast.walk(tree):
    if isinstance(node, ast.Call):
        fn = dotted_name(node.func)
        if fn.endswith("persist_research_rank_snapshot"):
            snapshot_calls.append(node)

def classify_rows_expr(rows_node: ast.AST) -> tuple[str, str]:
    label = expr_label(rows_node)

    enum_targets = []
    for child in ast.walk(rows_node):
        if not isinstance(child, ast.Call):
            continue
        if dotted_name(child.func) != "enumerate" or not child.args:
            continue
        enum_targets.append(dotted_name(child.args[0]) or expr_label(child.args[0]))

    if any(x == "adaylar" for x in enum_targets):
        return "ENUMERATES_DISPLAY_ADAYLAR", label

    if any(x == "filtrelenmis.adaylar" for x in enum_targets):
        return "ENUMERATES_FULL_FILTERED_ADAYLAR", label

    return "OTHER_ROWS_EXPRESSION", label

print()
print("=== AST: SNAPSHOT CALL CONTRACT ===")

classifications = []
if not snapshot_calls:
    print("SNAPSHOT_CALL=NONE")
else:
    for idx, call in enumerate(snapshot_calls, start=1):
        kw = {x.arg: x.value for x in call.keywords if x.arg}
        rows_node = kw.get("rows")
        source_node = kw.get("universe_source")
        profile_node = kw.get("profile_name")
        asof_node = kw.get("as_of")

        if rows_node is None:
            cls = "ROWS_KEYWORD_MISSING"
            rows_label = "-"
        else:
            cls, rows_label = classify_rows_expr(rows_node)

        classifications.append(cls)

        print(f"CALL={idx} LINE={call.lineno}")
        print(f"ROWS_CLASS={cls}")
        print(f"ROWS_EXPR={rows_label}")
        print(
            "AS_OF_EXPR="
            + (expr_label(asof_node) if asof_node is not None else "-")
        )
        print(
            "UNIVERSE_SOURCE_EXPR="
            + (expr_label(source_node) if source_node is not None else "-")
        )
        print(
            "PROFILE_NAME_EXPR="
            + (expr_label(profile_node) if profile_node is not None else "-")
        )

print()
print("=== DISPLAY-SLICE PROOF ===")

slice_confirmed = False
for _lineno, value in adaylar_assignments:
    text = expr_label(value).replace(" ", "")
    if "filtrelenmis.adaylar[:istek.maksimum_aday]" in text:
        slice_confirmed = True

print(f"ADAYLAR_IS_MAXIMUM_DISPLAY_SLICE={'YES' if slice_confirmed else 'NO'}")
print(
    "SNAPSHOT_ENUMERATES_DISPLAY_ADAYLAR="
    + ("YES" if "ENUMERATES_DISPLAY_ADAYLAR" in classifications else "NO")
)
print(
    "SNAPSHOT_ENUMERATES_FULL_FILTERED="
    + ("YES" if "ENUMERATES_FULL_FILTERED_ADAYLAR" in classifications else "NO")
)

print()
print("=== 25-AUG RANKING MEMORY SHAPE ===")

def parse_date(raw: str):
    value = str(raw or "").strip()
    for parser in (
        lambda x: date.fromisoformat(x),
        lambda x: date(
            int(x.split("/")[2]),
            int(x.split("/")[1]),
            int(x.split("/")[0]),
        ),
    ):
        try:
            return parser(value)
        except (ValueError, IndexError):
            pass
    return None

groups = defaultdict(list)
for line in memory_path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line:
        continue
    item = json.loads(line)
    if parse_date(item.get("as_of", "")) == date(2026, 8, 25):
        groups[
            (
                str(item.get("universe_source", "")),
                str(item.get("profile_name", "")),
            )
        ].append(item)

print(f"GROUP_COUNT={len(groups)}")
for (source_name, profile_name), rows in sorted(
    groups.items(),
    key=lambda p: (-len(p[1]), p[0][0], p[0][1]),
):
    ranks = sorted(int(x["rank"]) for x in rows)
    universe_sizes = sorted(
        {int(x["ranked_universe_size"]) for x in rows}
    )
    contiguous = ranks == list(range(1, len(ranks) + 1))
    print(
        f"SOURCE={source_name!r} PROFILE={profile_name!r} "
        f"ROWS={len(rows)} "
        f"MIN_RANK={ranks[0] if ranks else '-'} "
        f"MAX_RANK={ranks[-1] if ranks else '-'} "
        f"RANKED_UNIVERSE_SIZES={universe_sizes} "
        f"CONTIGUOUS_1_TO_N={'YES' if contiguous else 'NO'}"
    )

print()
print("=== BACKFILL REPORT FAILURE EVIDENCE ===")

report_path = Path(report_arg) if report_arg else None
if report_path and report_path.exists():
    report_lines = report_path.read_text(
        encoding="utf-8", errors="replace"
    ).splitlines()

    keys = (
        "25-AUG CONTRACT PARITY",
        "SOURCE=",
        "EXACT_25AUG",
        "BACKFILL_CONTRACT_BLOCKED",
        "BACKFILL_BLOCKED",
        "CROSS_CONTRACT",
        "KEY_CONFLICT",
        "Traceback",
        "RuntimeError",
        "ValueError",
        "TypeError",
    )

    selected = [
        line
        for line in report_lines
        if any(k in line for k in keys)
    ]

    if selected:
        for line in selected:
            print(line)
    else:
        print("NO_CLASSIFIED_ERROR_LINES_FOUND")
        print("REPORT_TAIL_BEGIN")
        for line in report_lines[-100:]:
            print(line)
        print("REPORT_TAIL_END")
else:
    print("REPORT_NOT_AVAILABLE")

print()
print("=== FINAL SNAPSHOT-HOOK DECISION ===")

display_persist = (
    slice_confirmed
    and "ENUMERATES_DISPLAY_ADAYLAR" in classifications
)

full_persist = (
    "ENUMERATES_FULL_FILTERED_ADAYLAR" in classifications
)

if display_persist:
    print(
        "SNAPSHOT_HOOK_CONTRACT=PROVEN_DISPLAY_SLICE"
    )
    print(
        "ROOT_CAUSE=CURRENT_RANKING_MEMORY_CAPTURE_PERSISTS_UI_DISPLAY_SLICE"
    )
    print(
        "IMPACT=RANKED_UNIVERSE_SIZE_IS_DISPLAY_COUNT_NOT_FULL_FILTERED_RESEARCH_COUNT"
    )
    print(
        "NEXT=PATCH_CAPTURE_HOOK_TO_FILTERED_ADAYLAR;"
        "ADD_REGRESSION_FOR_FULL_RESEARCH_SNAPSHOT;"
        "DO_NOT_BACKFILL_UNTIL_CURRENT_SNAPSHOT_CONTRACT_IS_REPAIRED"
    )
elif full_persist:
    print(
        "SNAPSHOT_HOOK_CONTRACT=PROVEN_FULL_FILTERED_RESEARCH"
    )
    print(
        "ROOT_CAUSE=NOT_SNAPSHOT_SLICE;USE_BACKFILL_REPORT_PARITY_FAILURE_AS_NEXT_TARGET"
    )
    print(
        "NEXT=DO_NOT_MUTATE;BUILD_PARITY_DIAGNOSTIC_FROM_REPORT_DETAILS"
    )
else:
    print(
        "SNAPSHOT_HOOK_CONTRACT=UNRESOLVED_CURRENT_EXPRESSION"
    )
    print(
        "NEXT=DO_NOT_MUTATE;USE_PRINTED_AST_ROWS_EXPR_AS_EXACT_PATCH_INPUT"
    )

print("SNAPSHOT_HOOK_CONTRACT_INSPECTION_V2=PASS")
'@

    [System.IO.File]::WriteAllText(
        $tmp,
        $code,
        (New-Object System.Text.UTF8Encoding($false))
    )

    & $Python $tmp $ProjectRoot $ReportPath
    if ($LASTEXITCODE -ne 0) {
        throw "SNAPSHOT_HOOK_CONTRACT_INSPECTION_V2_FAIL"
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
