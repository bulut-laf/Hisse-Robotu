param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

$Required = @(
    (Join-Path $ProjectRoot "backend\app\history\batch_historical_export.py"),
    (Join-Path $ProjectRoot "backend\app\analysis\market_scanner.py"),
    (Join-Path $ProjectRoot "backend\app\analysis\ranking_memory.py")
)

foreach ($p in $Required) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "REQUIRED_PATH_MISSING=$p"
    }
}

$oldPythonPath = $env:PYTHONPATH
$tmp = Join-Path $env:TEMP "hisse_daily10_replay_authority_proof_v1.py"

try {
    Write-Host "=== HISSE ROBOTU — REPLAY AUTHORITY PROOF V1 ==="
    Write-Host "MODE=READ_ONLY"
    Write-Host "PRODUCTION_MUTATION=NO"
    Write-Host "GOAL=ANSWER_CHECK_1_CHECK_2_CHECK_3_WITH_EVIDENCE"

    $env:PYTHONPATH = if ([string]::IsNullOrWhiteSpace($oldPythonPath)) {
        $ProjectRoot
    } else {
        "$ProjectRoot;$oldPythonPath"
    }

    $code = @'
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])

batch_path = root / "backend/app/history/batch_historical_export.py"
scanner_path = root / "backend/app/analysis/market_scanner.py"
memory_path = root / "backend/app/analysis/ranking_memory.py"

batch = batch_path.read_text(encoding="utf-8")
scanner = scanner_path.read_text(encoding="utf-8")
memory = memory_path.read_text(encoding="utf-8")

def yn(value: bool) -> str:
    return "YES" if value else "NO"

def source_defs(path: Path):
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    out = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            seg = ast.get_source_segment(text, node) or ""
            out.append((node.name, node.lineno, seg))
    return out

canonical_tokens = (
    "BistMarketScannerService",
    "MarketScanResult",
    "observations_from_research_rows",
    "aday_tablosu_kayitlari",
    "tarama_sonucunu_filtrele",
)
batch_canonical_hits = [token for token in canonical_tokens if token in batch]

print()
print("=== CHECK 1 — SAME CANONICAL RESEARCH ROWS? ===")
print("BATCH_CANONICAL_TOKENS=" + (",".join(batch_canonical_hits) or "NONE"))

row_rank_evidence = any(
    token in batch
    for token in (
        '"Sıra"', "'Sıra'", '"Sira"', "'Sira'",
        '"rank"', "'rank'",
    )
)
row_symbol_evidence = any(
    token in batch
    for token in (
        '"Hisse"', "'Hisse'", '"symbol"', "'symbol'",
    )
)

print(f"BATCH_HAS_RANK_FIELD_EVIDENCE={yn(row_rank_evidence)}")
print(f"BATCH_HAS_SYMBOL_FIELD_EVIDENCE={yn(row_symbol_evidence)}")

check1 = bool(batch_canonical_hits) and row_rank_evidence and row_symbol_evidence

if check1:
    print("CHECK_1=PASS")
    print("CHECK_1_REASON=Batch replay is directly wired to canonical Research-row semantics.")
else:
    print("CHECK_1=FAIL")
    print(
        "CHECK_1_REASON=batch_historical_export is not proven to recreate "
        "the exact canonical Research rows consumed by ranking_memory."
    )

print()
print("=== CHECK 2 — CUT-DATE UNIVERSE / PROFILE COMPARABILITY? ===")

has_cut_date = "cut_date" in batch
has_universe = "universe" in batch.lower() or "evren" in batch.lower()
has_profile = "profile" in batch.lower() or "profil" in batch.lower()

print(f"BATCH_HAS_CUT_DATE={yn(has_cut_date)}")
print(f"BATCH_HAS_UNIVERSE_CONTEXT={yn(has_universe)}")
print(f"BATCH_HAS_PROFILE_CONTEXT={yn(has_profile)}")

memory_requires_universe = "universe_source" in memory
memory_requires_profile = "profile_name" in memory
print(f"RANKING_MEMORY_REQUIRES_UNIVERSE_SOURCE={yn(memory_requires_universe)}")
print(f"RANKING_MEMORY_REQUIRES_PROFILE_NAME={yn(memory_requires_profile)}")

check2 = (
    has_cut_date
    and has_universe
    and has_profile
    and memory_requires_universe
    and memory_requires_profile
)

if check2:
    print("CHECK_2=PASS")
    print(
        "CHECK_2_REASON=Replay contract exposes cut-date plus universe/profile "
        "context required by Ranking Memory."
    )
else:
    print("CHECK_2=FAIL")
    missing = []
    if not has_cut_date:
        missing.append("cut_date")
    if not has_universe:
        missing.append("universe")
    if not has_profile:
        missing.append("profile")
    print("CHECK_2_MISSING=" + ",".join(missing))
    print(
        "CHECK_2_REASON=Historical replay cannot yet be treated as comparable "
        "Ranking Memory input without these proven dimensions."
    )

print()
print("=== CHECK 3 — NO FUTURE LEAKAGE + >=6 SESSIONS? ===")

future_guard_terms = (
    "cut_date",
    "<= cutoff",
    "<= cut_date",
    "loc[:",
    "truncate",
    "end_date",
)
future_guard_hits = [term for term in future_guard_terms if term in batch]

request_range_evidence = (
    ("start_date" in batch and "end_date" in batch)
    or ("cut_date" in batch and "timedelta" in batch)
)

print("FUTURE_GUARD_TERMS=" + (",".join(future_guard_hits) or "NONE"))
print(f"DATE_RANGE_REQUEST_EVIDENCE={yn(request_range_evidence)}")

# Search exact repo candidates where historical/cut-date is combined with canonical scanner.
print()
print("=== CANONICAL HISTORICAL REPLAY CANDIDATES ===")

candidate_rows = []
for path in (root / "backend/app").rglob("*.py"):
    if "__pycache__" in path.parts:
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8-sig")

    low = text.lower()
    historical = any(k in low for k in ("cut_date", "cutoff_date", "historical", "tarihsel", "replay"))
    canonical = any(k in text for k in ("BistMarketScannerService", "MarketScanResult"))
    rank_rows = any(k in text for k in ("observations_from_research_rows", '"Sıra"', "'Sıra'"))

    if historical and (canonical or rank_rows):
        score = int(historical) + 2 * int(canonical) + 2 * int(rank_rows)
        candidate_rows.append((score, path, canonical, rank_rows))

for score, path, canonical, rank_rows in sorted(
    candidate_rows,
    key=lambda x: (-x[0], str(x[1]))
)[:30]:
    print(
        f"CANDIDATE score={score} path={path.relative_to(root)} "
        f"canonical_scanner={yn(canonical)} rank_rows={yn(rank_rows)}"
    )

canonical_replay_candidates = [
    row for row in candidate_rows if row[2] and row[3]
]

# Static evidence cannot prove the system can actually complete 6 sessions.
check3_static = bool(future_guard_hits) and request_range_evidence and bool(canonical_replay_candidates)

if check3_static:
    print("CHECK_3_STATIC=PASS")
    print(
        "CHECK_3_STATIC_REASON=At least one canonical rank replay candidate and "
        "date-boundary evidence exist. Runtime 6-session dry-run is still required."
    )
else:
    print("CHECK_3_STATIC=FAIL")
    print(
        "CHECK_3_STATIC_REASON=No fully proven canonical rank replay seam with "
        "future-boundary evidence was found."
    )

print()
print("=== FINAL REPLAY AUTHORITY DECISION ===")

if check1 and check2 and check3_static:
    print("REPLAY_AUTHORITY=PROVISIONALLY_PROVEN")
    print("NEXT=RUN_6_SESSION_READ_ONLY_DRY_RUN")
elif canonical_replay_candidates:
    print("REPLAY_AUTHORITY=ALTERNATE_CANONICAL_SEAM_FOUND")
    print("NEXT=INSPECT_AND_RUN_EXACT_ALTERNATE_SEAM_DRY_RUN")
else:
    print("REPLAY_AUTHORITY=NOT_PROVEN")
    print(
        "NEXT=DO_NOT_BACKFILL_AND_DO_NOT_RELAX_TRAJECTORY_RULE;"
        "BUILD_OR_REUSE_CANONICAL_CUT_DATE_RESEARCH_REPLAY_FIRST"
    )

print("REPLAY_AUTHORITY_PROOF=PASS")
'@

    [System.IO.File]::WriteAllText(
        $tmp,
        $code,
        (New-Object System.Text.UTF8Encoding($false))
    )

    & $Python $tmp $ProjectRoot
    if ($LASTEXITCODE -ne 0) {
        throw "REPLAY_AUTHORITY_PROOF_FAIL"
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
