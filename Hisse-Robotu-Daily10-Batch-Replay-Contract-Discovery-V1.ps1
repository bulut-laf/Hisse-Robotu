param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Target = Join-Path $ProjectRoot "backend\app\history\batch_historical_export.py"

foreach ($p in @($Python,$Target)) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "REQUIRED_PATH_MISSING=$p"
    }
}

$oldPythonPath = $env:PYTHONPATH
$tmp = Join-Path $env:TEMP "hisse_daily10_batch_replay_contract_discovery_v1.py"

try {
    Write-Host "=== HISSE ROBOTU — BATCH REPLAY CONTRACT DISCOVERY V1 ==="
    Write-Host "MODE=READ_ONLY"
    Write-Host "PRODUCTION_MUTATION=NO"
    Write-Host "GOAL=PROVE_HISTORICAL_REPLAY_CAN_RECREATE_AUTHORITATIVE_RESEARCH_RANKS"

    $env:PYTHONPATH = if ([string]::IsNullOrWhiteSpace($oldPythonPath)) {
        $ProjectRoot
    } else {
        "$ProjectRoot;$oldPythonPath"
    }

    $code = @'
from __future__ import annotations

import ast
import dataclasses
import importlib
import inspect
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
target = root / "backend/app/history/batch_historical_export.py"

print(f"TARGET={target}")
text = target.read_text(encoding="utf-8")
tree = ast.parse(text, filename=str(target))

print()
print("=== TOP-LEVEL IMPORTS ===")
for node in tree.body:
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        seg = ast.get_source_segment(text, node) or ""
        print(seg.replace("\n", " "))

print()
print("=== TOP-LEVEL DEFINITIONS ===")
for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        kind = type(node).__name__
        print(f"{kind} {node.name} line={node.lineno}")

print()
print("=== RUNTIME PUBLIC SIGNATURES ===")
module = importlib.import_module("backend.app.history.batch_historical_export")
for name in sorted(dir(module)):
    if name.startswith("_"):
        continue
    obj = getattr(module, name)
    if inspect.isfunction(obj) and obj.__module__ == module.__name__:
        try:
            sig = inspect.signature(obj)
        except (TypeError, ValueError):
            sig = "?"
        print(f"FUNCTION {name}{sig}")
    elif inspect.isclass(obj) and obj.__module__ == module.__name__:
        try:
            sig = inspect.signature(obj)
        except (TypeError, ValueError):
            sig = "?"
        print(f"CLASS {name}{sig}")
        if dataclasses.is_dataclass(obj):
            print(
                "  DATACLASS_FIELDS="
                + ",".join(field.name for field in dataclasses.fields(obj))
            )

print()
print("=== RELEVANT SOURCE BLOCKS ===")
terms = (
    "combined_rows",
    "cut_date",
    "start_date",
    "end_date",
    "rows",
    "universe",
    "candidate",
    "rank",
    "score",
)
for node in tree.body:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        continue
    seg = ast.get_source_segment(text, node) or ""
    low = seg.lower()
    if any(term in low for term in terms):
        print()
        print(f"--- {type(node).__name__} {node.name} @L{node.lineno} ---")
        lines = seg.splitlines()
        for line in lines[:180]:
            print(line)
        if len(lines) > 180:
            print("...TRUNCATED...")

print()
print("=== RELATED REPLAY / HISTORICAL FILES ===")
candidates = []
for base in (root / "backend/app/history", root / "backend/app/analysis"):
    if not base.exists():
        continue
    for path in base.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        name_low = path.name.lower()
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            source = path.read_text(encoding="utf-8-sig")
        low = source.lower()
        score = 0
        for token in (
            "historical", "replay", "cut_date", "batch",
            "walk_forward", "candidate", "rank", "research",
        ):
            if token in name_low:
                score += 3
            if token in low:
                score += 1
        if score >= 5:
            candidates.append((score, path, source))

for score, path, source in sorted(candidates, key=lambda x: (-x[0], str(x[1])))[:30]:
    print(f"FILE score={score} path={path.relative_to(root)}")
    try:
        t = ast.parse(source, filename=str(path))
    except SyntaxError:
        continue
    defs = [
        n.name
        for n in t.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    if defs:
        print("  DEFS=" + ", ".join(defs[:30]))

print()
print("=== RESEARCH-RANK CONTRACT SEARCH ===")
patterns = (
    "aday_tablosu_kayitlari",
    "observations_from_research_rows",
    "MarketScanResult",
    "BistMarketScannerService",
    "tarama_sonucunu_filtrele",
    "Sıra",
    "Sira",
    "rank",
)
hits = []
for base in (root / "backend/app",):
    for path in base.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            lines = path.read_text(encoding="utf-8-sig").splitlines()
        for i, line in enumerate(lines, start=1):
            if any(p in line for p in patterns):
                if (
                    "ranking_memory" in str(path)
                    or "market_scanner" in str(path)
                    or "batch_historical" in str(path)
                    or "replay" in str(path).lower()
                    or "histor" in str(path).lower()
                ):
                    hits.append((path, i, line.strip()))

for path, i, line in hits[:180]:
    print(f"HIT={path.relative_to(root)}:{i}::{line}")

print()
print("=== DECISION INPUT ===")
print(
    "CHECK_1=Does historical replay produce the same canonical Research rows "
    "used by observations_from_research_rows?"
)
print(
    "CHECK_2=Does replay preserve cut-date universe/profile comparability?"
)
print(
    "CHECK_3=Can at least 6 completed sessions be replayed without future leakage?"
)
print("BATCH_REPLAY_CONTRACT_DISCOVERY=PASS")
'@

    [System.IO.File]::WriteAllText(
        $tmp,
        $code,
        (New-Object System.Text.UTF8Encoding($false))
    )

    & $Python $tmp $ProjectRoot
    if ($LASTEXITCODE -ne 0) {
        throw "BATCH_REPLAY_CONTRACT_DISCOVERY_FAIL"
    }
}
finally {
    if (Test-Path -LiteralPath $tmp) {
        Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
    }
    if ($null -eq $oldPythonPath) {
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    } else {
        $env:PYTHONPATH = $oldPythonPath
    }
}
