param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$MemoryFile = Join-Path $ProjectRoot "data\ranking_memory\rank_observations.jsonl"

foreach ($p in @($Python, $MemoryFile)) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "REQUIRED_PATH_MISSING=$p"
    }
}

$oldPythonPath = $env:PYTHONPATH
$tmp = Join-Path $env:TEMP "hisse_daily10_ranking_memory_write_lineage_v1.py"

try {
    Write-Host "=== HISSE ROBOTU — RANKING MEMORY WRITE LINEAGE V1 ==="
    Write-Host "MODE=READ_ONLY"
    Write-Host "PRODUCTION_MUTATION=NO"
    Write-Host "GOAL=FIND_CURRENT_AUTHORITATIVE_RANKING_MEMORY_WRITER"

    $env:PYTHONPATH = if ([string]::IsNullOrWhiteSpace($oldPythonPath)) {
        $ProjectRoot
    } else {
        "$ProjectRoot;$oldPythonPath"
    }

    $code = @'
from __future__ import annotations

import ast
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

root = Path(sys.argv[1])
memory_path = root / "data" / "ranking_memory" / "rank_observations.jsonl"

skip_dirs = {
    ".git", ".venv", "node_modules", "__pycache__",
    ".pytest_cache", "_rollback",
}

needles = (
    "persist_research_rank_snapshot",
    "append_snapshot",
    "observations_from_research_rows",
    "RankObservationJsonlStore",
    "rank_observations.jsonl",
    "ranking_snapshot_adapter",
)

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

print()
print("=== REPO-WIDE TEXT HITS ===")

text_hits = []
for path in iter_py_files(root):
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        continue
    found = [n for n in needles if n in text]
    if found:
        rel = path.relative_to(root)
        text_hits.append((str(rel), found))
        print(f"FILE={rel} HITS={','.join(found)}")

print(f"TEXT_HIT_FILE_COUNT={len(text_hits)}")

print()
print("=== AST WRITE-CALL INVENTORY ===")

write_calls = []
adapter_calls = []
observation_calls = []

for path in iter_py_files(root):
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(text)
    except (OSError, SyntaxError):
        continue

    rel = str(path.relative_to(root))

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        fn = dotted(node.func)

        if fn.endswith("append_snapshot"):
            write_calls.append((rel, node.lineno, fn, unparse(node)))
        elif fn.endswith("persist_research_rank_snapshot"):
            adapter_calls.append((rel, node.lineno, fn, unparse(node)))
        elif fn.endswith("observations_from_research_rows"):
            observation_calls.append((rel, node.lineno, fn, unparse(node)))

if not write_calls:
    print("APPEND_SNAPSHOT_CALLS=NONE")
else:
    for rel, lineno, fn, expr in write_calls:
        print(f"APPEND_CALL file={rel} line={lineno} fn={fn}")
        print(f"EXPR={expr}")

if not adapter_calls:
    print("PERSIST_ADAPTER_CALLS=NONE")
else:
    for rel, lineno, fn, expr in adapter_calls:
        print(f"PERSIST_CALL file={rel} line={lineno} fn={fn}")
        print(f"EXPR={expr}")

if not observation_calls:
    print("OBSERVATION_BUILD_CALLS=NONE")
else:
    for rel, lineno, fn, expr in observation_calls:
        print(f"OBSERVATION_CALL file={rel} line={lineno} fn={fn}")
        print(f"EXPR={expr}")

print()
print("=== RANKING SNAPSHOT ADAPTER SOURCE ===")

adapter_path = root / "backend" / "app" / "analysis" / "ranking_snapshot_adapter.py"
if adapter_path.exists():
    adapter_text = adapter_path.read_text(encoding="utf-8", errors="replace")
    print(f"ADAPTER_EXISTS=YES PATH={adapter_path.relative_to(root)}")
    for i, line in enumerate(adapter_text.splitlines(), start=1):
        print(f"{i:04d}: {line}")
else:
    print("ADAPTER_EXISTS=NO")

print()
print("=== MARKET SCANNER IMPORT / CALL STATUS ===")

market_path = root / "backend" / "app" / "analysis" / "market_scanner.py"
if market_path.exists():
    market_text = market_path.read_text(encoding="utf-8", errors="replace")
    print(
        "MARKET_IMPORTS_RANKING_SNAPSHOT_ADAPTER="
        + ("YES" if "ranking_snapshot_adapter" in market_text else "NO")
    )
    print(
        "MARKET_CONTAINS_PERSIST_CALL_TEXT="
        + (
            "YES"
            if re.search(r"\bpersist_research_rank_snapshot\s*\(", market_text)
            else "NO"
        )
    )
else:
    print("MARKET_SCANNER_MISSING=YES")

print()
print("=== 25-AUG MEMORY CONTRACT GROUPS ===")

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
lines = memory_path.read_text(encoding="utf-8").splitlines()

for raw in lines:
    raw = raw.strip()
    if not raw:
        continue
    item = json.loads(raw)
    if parse_date(item.get("as_of", "")) == date(2026, 8, 25):
        groups[
            (
                str(item.get("universe_source", "")),
                str(item.get("profile_name", "")),
            )
        ].append(item)

print(f"GROUP_COUNT={len(groups)}")
for (source, profile), rows in sorted(
    groups.items(),
    key=lambda p: (-len(p[1]), p[0][0], p[0][1]),
):
    ranks = sorted(int(x["rank"]) for x in rows)
    sizes = sorted({int(x["ranked_universe_size"]) for x in rows})
    contiguous = ranks == list(range(1, len(ranks) + 1))
    print(
        f"SOURCE={source!r} PROFILE={profile!r} "
        f"ROWS={len(rows)} "
        f"MIN_RANK={ranks[0] if ranks else '-'} "
        f"MAX_RANK={ranks[-1] if ranks else '-'} "
        f"RANKED_UNIVERSE_SIZES={sizes} "
        f"CONTIGUOUS_1_TO_N={'YES' if contiguous else 'NO'}"
    )

print()
print("=== FILE METADATA ===")
stat = memory_path.stat()
print(f"MEMORY_BYTES={stat.st_size}")
print(f"MEMORY_MTIME_EPOCH={stat.st_mtime}")

print()
print("=== FINAL WRITE-LINEAGE DECISION ===")

production_write_calls = [
    row for row in write_calls
    if not row[0].startswith("backend/tests/")
]
production_adapter_calls = [
    row for row in adapter_calls
    if not row[0].startswith("backend/tests/")
]

if production_adapter_calls:
    print("RANKING_MEMORY_WRITE_LINEAGE=PROVEN_VIA_PERSIST_ADAPTER_CALL")
    print(
        "NEXT=INSPECT_EXACT_CALL_ROWS_EXPRESSION_AND_REPAIR_ONLY_IF_CURRENT_CONTRACT_IS_PARTIAL"
    )
elif production_write_calls:
    print("RANKING_MEMORY_WRITE_LINEAGE=PROVEN_DIRECT_APPEND")
    print(
        "NEXT=INSPECT_DIRECT_APPEND_INPUT_CONTRACT_BEFORE_BACKFILL"
    )
elif adapter_path.exists():
    print("RANKING_MEMORY_WRITE_LINEAGE=NO_CURRENT_PRODUCTION_CALLER")
    print(
        "INTERPRETATION=RANKING_MEMORY_FILE_EXISTS_BUT_CURRENT_REPO_HAS_NO_PRODUCTION_WRITE_SEAM"
    )
    print(
        "NEXT=DO_NOT_BACKFILL_OR_PATCH_MARKET_SCANNER;"
        "TRACE_HISTORICAL_CREATION_SOURCE_FROM_GIT_OR_OPERATION_REPORTS"
    )
else:
    print("RANKING_MEMORY_WRITE_LINEAGE=NO_WRITER_PROVEN")
    print(
        "NEXT=DO_NOT_MUTATE;TRACE_HISTORICAL_CREATION_SOURCE"
    )

print("RANKING_MEMORY_WRITE_LINEAGE_V1=PASS")
'@

    [System.IO.File]::WriteAllText(
        $tmp,
        $code,
        (New-Object System.Text.UTF8Encoding($false))
    )

    & $Python $tmp $ProjectRoot
    if ($LASTEXITCODE -ne 0) {
        throw "RANKING_MEMORY_WRITE_LINEAGE_V1_FAIL"
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
