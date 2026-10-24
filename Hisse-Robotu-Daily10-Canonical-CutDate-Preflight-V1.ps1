param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

$Required = @(
    (Join-Path $ProjectRoot "backend\app\analysis\market_scanner.py"),
    (Join-Path $ProjectRoot "backend\app\analysis\stock_scanner.py"),
    (Join-Path $ProjectRoot "backend\app\analysis\ranking_memory.py")
)

foreach ($p in $Required) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "REQUIRED_PATH_MISSING=$p"
    }
}

$oldPythonPath = $env:PYTHONPATH
$tmp = Join-Path $env:TEMP "hisse_daily10_canonical_cutdate_preflight_v1.py"

try {
    Write-Host "=== HISSE ROBOTU — CANONICAL CUT-DATE RESEARCH REPLAY PREFLIGHT V1 ==="
    Write-Host "MODE=READ_ONLY"
    Write-Host "PRODUCTION_MUTATION=NO"
    Write-Host "GOAL=FIND_MINIMAL_CANONICAL_CUT_DATE_REPLAY_SEAM"

    $env:PYTHONPATH = if ([string]::IsNullOrWhiteSpace($oldPythonPath)) {
        $ProjectRoot
    } else {
        "$ProjectRoot;$oldPythonPath"
    }

    $code = @'
from __future__ import annotations

import ast
import inspect
import importlib
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])

focus = [
    root / "backend/app/analysis/market_scanner.py",
    root / "backend/app/analysis/stock_scanner.py",
    root / "backend/app/analysis/stock_analyzer.py",
    root / "backend/app/analysis/bist_universe.py",
    root / "backend/app/analysis/scan_filter.py",
    root / "backend/app/analysis/scan_profiles.py",
    root / "backend/app/data/market_data.py",
    root / "backend/app/data/batch_market_data.py",
    root / "backend/app/analysis/ranking_memory.py",
]
focus = [p for p in focus if p.exists()]

def load_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig")

def yn(v: bool) -> str:
    return "YES" if v else "NO"

def signature_lines(path: Path):
    text = load_text(path)
    tree = ast.parse(text, filename=str(path))
    rows = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = []
            for a in list(node.args.args) + list(node.args.kwonlyargs):
                args.append(a.arg)
            rows.append((node.name, node.lineno, tuple(args)))
    return rows

print()
print("=== FOCUS FILES ===")
for p in focus:
    print(f"FILE={p.relative_to(root)}")

print()
print("=== EXACT FUNCTION SIGNATURE INPUTS ===")
for p in focus:
    try:
        rows = signature_lines(p)
    except SyntaxError as exc:
        print(f"PARSE_ERROR={p.relative_to(root)}::{exc}")
        continue

    interesting = {
        "calistir", "tara", "analiz_et", "analyze", "fiyat_verisi_getir",
        "guvenli_fiyat_verisi_getir", "toplu_fiyat_verisi_getir",
        "download", "fetch", "load", "yukle", "tarama_evreni_yukle",
    }
    for name, line, args in rows:
        if (
            name in interesting
            or "date" in " ".join(args).lower()
            or "tarih" in " ".join(args).lower()
            or "end" in " ".join(args).lower()
            or "as_of" in " ".join(args).lower()
            or "cut" in " ".join(args).lower()
        ):
            print(
                f"SIG={p.relative_to(root)}:{line}::{name}"
                f"({','.join(args)})"
            )

print()
print("=== MARKET SCANNER CONTRACT ===")
market = load_text(root / "backend/app/analysis/market_scanner.py")
stock = load_text(root / "backend/app/analysis/stock_scanner.py")
universe_path = root / "backend/app/analysis/bist_universe.py"
universe = load_text(universe_path) if universe_path.exists() else ""

market_has_cut = bool(re.search(
    r"def\s+calistir\s*\([^)]*(cut|as_of|tarih|date)",
    market,
    flags=re.I | re.S,
))
stock_tara_has_cut = bool(re.search(
    r"def\s+tara\s*\([^)]*(cut|as_of|tarih|date|end)",
    stock,
    flags=re.I | re.S,
))
market_passes_cut = bool(re.search(
    r"\.tara\s*\([^)]*(cut|as_of|tarih|date|end)",
    market,
    flags=re.I | re.S,
))

print(f"MARKET_SCANNER_ACCEPTS_CUT_DATE={yn(market_has_cut)}")
print(f"BATCH_STOCK_SCANNER_TARA_ACCEPTS_CUT_DATE={yn(stock_tara_has_cut)}")
print(f"MARKET_SCANNER_PASSES_CUT_DATE_TO_TARA={yn(market_passes_cut)}")

print()
print("=== STOCK SCANNER DATA-SEAM EVIDENCE ===")

provider_terms = (
    "downloader", "provider", "market_data", "fiyat_verisi",
    "fetch", "download", "loader", "repository", "veri_saglayici",
)
date_terms = (
    "start_date", "end_date", "cut_date", "cutoff_date",
    "as_of", "analysis_date", "tarih", "date",
)

for term in provider_terms:
    if term.lower() in stock.lower():
        print(f"STOCK_SCANNER_PROVIDER_TERM={term}")

stock_date_hits = [term for term in date_terms if term.lower() in stock.lower()]
print("STOCK_SCANNER_DATE_TERMS=" + (",".join(stock_date_hits) or "NONE"))

# Search all app Python files for data functions which expose an explicit upper date boundary.
boundary_candidates = []
for path in (root / "backend/app").rglob("*.py"):
    if "__pycache__" in path.parts:
        continue
    text = load_text(path)
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        continue
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        args = [a.arg for a in list(node.args.args) + list(node.args.kwonlyargs)]
        lowargs = {a.lower() for a in args}
        boundary = any(
            key in lowargs
            for key in (
                "end_date", "cut_date", "cutoff_date",
                "as_of", "analysis_date", "today",
            )
        )
        dataish = any(
            token in node.name.lower()
            for token in (
                "data", "veri", "download", "fetch", "load",
                "price", "fiyat", "bar",
            )
        )
        if boundary and dataish:
            boundary_candidates.append(
                (path, node.lineno, node.name, tuple(args))
            )

print()
print("=== EXPLICIT UPPER-DATE DATA CANDIDATES ===")
for path, line, name, args in boundary_candidates[:60]:
    print(
        f"BOUNDARY={path.relative_to(root)}:{line}::"
        f"{name}({','.join(args)})"
    )
print(f"BOUNDARY_CANDIDATE_COUNT={len(boundary_candidates)}")

print()
print("=== UNIVERSE AS-OF CONTRACT ===")
universe_asof = bool(re.search(
    r"def\s+\w+\s*\([^)]*(as_of|cut|tarih|date)",
    universe,
    flags=re.I | re.S,
))
universe_history_words = [
    token for token in (
        "history", "historical", "archive", "snapshot",
        "as_of", "effective_date", "cut_date",
    )
    if token in universe.lower()
]
print(f"UNIVERSE_ACCEPTS_DATE_INPUT={yn(universe_asof)}")
print(
    "UNIVERSE_HISTORY_TERMS="
    + (",".join(universe_history_words) or "NONE")
)

print()
print("=== PROFILE COMPARABILITY CONTRACT ===")
profile_ok = (
    "profil_adi" in market
    and "profil_al" in market
)
print(f"PROFILE_NAME_IS_EXPLICIT={yn(profile_ok)}")

print()
print("=== CANONICAL ROW CONTRACT ===")
memory = load_text(root / "backend/app/analysis/ranking_memory.py")
memory_rows = "observations_from_research_rows" in memory
memory_universe = "universe_source" in memory
memory_profile = "profile_name" in memory
print(f"RANKING_MEMORY_RESEARCH_ROW_ADAPTER={yn(memory_rows)}")
print(f"RANKING_MEMORY_UNIVERSE_KEY={yn(memory_universe)}")
print(f"RANKING_MEMORY_PROFILE_KEY={yn(memory_profile)}")

print()
print("=== MINIMAL PATCH FEASIBILITY DECISION ===")

data_boundary_proven = len(boundary_candidates) > 0
canonical_gap = not (
    market_has_cut
    and stock_tara_has_cut
    and market_passes_cut
)

if canonical_gap and data_boundary_proven and universe_asof and profile_ok:
    print("CUTDATE_REPLAY_FEASIBILITY=READY_FOR_MINIMAL_OPT_IN_ADAPTER")
    print(
        "NEXT=ADD_READ_ONLY_OPT_IN_CUT_DATE_THROUGH_CANONICAL_MARKET_SCANNER;"
        "NO_DEFAULT_BEHAVIOR_CHANGE"
    )
elif canonical_gap and data_boundary_proven and not universe_asof and profile_ok:
    print("CUTDATE_REPLAY_FEASIBILITY=PRICE_SEAM_READY_UNIVERSE_ASOF_GAP")
    print(
        "NEXT=DO_NOT_PATCH_RANKING_MEMORY;"
        "PROVE_OR_ADD_READ_ONLY_HISTORICAL_UNIVERSE_SNAPSHOT_INPUT_FIRST"
    )
elif canonical_gap and not data_boundary_proven:
    print("CUTDATE_REPLAY_FEASIBILITY=DATA_BOUNDARY_GAP")
    print(
        "NEXT=DO_NOT_PATCH_MARKET_SCANNER;"
        "IDENTIFY_SAFE_PRICE_DATA_UPPER_BOUNDARY_ADAPTER_FIRST"
    )
else:
    print("CUTDATE_REPLAY_FEASIBILITY=EXISTING_CUTDATE_SEAM_PRESENT")
    print("NEXT=RUN_6_SESSION_READ_ONLY_CANONICAL_REPLAY_DRY_RUN")

print("CANONICAL_CUTDATE_PREFLIGHT=PASS")
'@

    [System.IO.File]::WriteAllText(
        $tmp,
        $code,
        (New-Object System.Text.UTF8Encoding($false))
    )

    & $Python $tmp $ProjectRoot
    if ($LASTEXITCODE -ne 0) {
        throw "CANONICAL_CUTDATE_PREFLIGHT_FAIL"
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
