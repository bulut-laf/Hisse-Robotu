param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$BatchExport = Join-Path $ProjectRoot "backend\app\history\batch_historical_export.py"
$ScanHistory = Join-Path $ProjectRoot "backend\app\history\scan_history.py"
$RankingMemory = Join-Path $ProjectRoot "backend\app\analysis\ranking_memory.py"

foreach ($p in @($Python,$RankingMemory)) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "REQUIRED_PATH_MISSING=$p"
    }
}

$oldPythonPath = $env:PYTHONPATH
$tmp = Join-Path $env:TEMP "hisse_daily10_backfill_feasibility_v1.py"

try {
    Write-Host "=== HISSE ROBOTU — DAILY10 BACKFILL FEASIBILITY V1 ==="
    Write-Host "MODE=READ_ONLY"
    Write-Host "PRODUCTION_MUTATION=NO"
    Write-Host "GOAL=AUTHORITATIVE_HISTORICAL_RESEARCH_RANK_BACKFILL"

    Write-Host ("BATCH_HISTORICAL_EXPORT_EXISTS=" + (Test-Path -LiteralPath $BatchExport))
    Write-Host ("SCAN_HISTORY_EXISTS=" + (Test-Path -LiteralPath $ScanHistory))
    Write-Host ("RANKING_MEMORY_EXISTS=" + (Test-Path -LiteralPath $RankingMemory))

    $env:PYTHONPATH = if ([string]::IsNullOrWhiteSpace($oldPythonPath)) {
        $ProjectRoot
    } else {
        "$ProjectRoot;$oldPythonPath"
    }

    $code = @'
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

root = Path(sys.argv[1])

skip_parts = {
    ".git", ".venv", "__pycache__", "_rollback",
    "node_modules", ".pytest_cache",
}

roots = [
    root / "data",
    root / "exports",
    root / "_discovery",
    root / "backend" / "data",
    root / "backend" / "exports",
]
roots = [p for p in roots if p.exists()]

rank_aliases = {
    "sıra", "sira", "rank", "ranking", "research rank", "research_rank",
}
symbol_aliases = {
    "hisse", "symbol", "sembol", "ticker",
}
date_aliases = {
    "tarih", "date", "cut_date", "as_of", "veri tarihi", "veri_tarihi",
}
universe_aliases = {
    "evren", "universe", "universe_source", "evren_kaynagi",
}
profile_aliases = {
    "profil", "profile", "profile_name", "profil_adi",
}

date_re = re.compile(r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})")

def norm(value):
    return str(value or "").strip().lower().replace("\ufeff", "")

def pick(headers, aliases):
    by_norm = {norm(h): h for h in headers}
    for alias in aliases:
        if alias in by_norm:
            return by_norm[alias]
    return None

def infer_date(path):
    m = date_re.search(path.name)
    if not m:
        return None
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

def iter_files():
    seen = set()
    for base in roots:
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if any(part in skip_parts for part in path.parts):
                continue
            if path.suffix.lower() not in {".csv", ".json", ".jsonl"}:
                continue
            try:
                key = str(path.resolve())
            except OSError:
                key = str(path)
            if key in seen:
                continue
            seen.add(key)
            yield path

csv_candidates = []
json_candidates = []
errors = []

for path in iter_files():
    suffix = path.suffix.lower()
    if suffix == ".csv":
        try:
            raw = path.read_text(encoding="utf-8-sig", errors="replace")
            sample = raw[:65536]
            if not sample.strip():
                continue
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
                delimiter = dialect.delimiter
            except csv.Error:
                delimiter = ","
            reader = csv.DictReader(raw.splitlines(), delimiter=delimiter)
            headers = tuple(reader.fieldnames or ())
            symbol_col = pick(headers, symbol_aliases)
            rank_col = pick(headers, rank_aliases)
            if not symbol_col or not rank_col:
                continue

            rows = []
            dates = set()
            date_col = pick(headers, date_aliases)
            universe_col = pick(headers, universe_aliases)
            profile_col = pick(headers, profile_aliases)

            for idx, row in enumerate(reader):
                if idx >= 3000:
                    break
                symbol = str(row.get(symbol_col) or "").strip()
                rank = str(row.get(rank_col) or "").strip()
                if not symbol or not rank:
                    continue
                rows.append(row)
                if date_col:
                    d = str(row.get(date_col) or "").strip()
                    if d:
                        dates.add(d[:10])

            inferred = infer_date(path)
            if inferred:
                dates.add(inferred)

            csv_candidates.append(
                {
                    "path": path,
                    "headers": headers,
                    "symbol_col": symbol_col,
                    "rank_col": rank_col,
                    "date_col": date_col,
                    "universe_col": universe_col,
                    "profile_col": profile_col,
                    "rows": len(rows),
                    "dates": sorted(dates),
                }
            )
        except Exception as exc:
            errors.append((path, f"{type(exc).__name__}: {exc}"))

    elif suffix in {".json", ".jsonl"}:
        name_low = path.name.lower()
        if not any(k in name_low for k in ("scan", "research", "candidate", "history", "snapshot")):
            continue
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            lower = text[:200000].lower()
            if (
                ("hisse" in lower or "symbol" in lower or "sembol" in lower)
                and ("sıra" in lower or '"rank"' in lower or "sira" in lower)
            ):
                json_candidates.append(path)
        except Exception as exc:
            errors.append((path, f"{type(exc).__name__}: {exc}"))

print()
print("=== AUTHORITATIVE-SEAM SOURCE CODE ===")
for rel in (
    "backend/app/history/batch_historical_export.py",
    "backend/app/history/scan_history.py",
    "backend/app/history/scan_history_reader.py",
):
    p = root / rel
    print(f"{rel}={'YES' if p.exists() else 'NO'}")

print()
print("=== CSV RANK SNAPSHOT CANDIDATES ===")
print(f"CSV_CANDIDATE_COUNT={len(csv_candidates)}")
for item in sorted(
    csv_candidates,
    key=lambda x: (len(x["dates"]), x["rows"]),
    reverse=True,
)[:30]:
    rel = item["path"].relative_to(root)
    dates = ",".join(item["dates"][:10]) if item["dates"] else "-"
    print(
        f"CSV={rel} | rows={item['rows']} | dates={dates} | "
        f"symbol={item['symbol_col']} | rank={item['rank_col']} | "
        f"date_col={item['date_col'] or '-'} | "
        f"universe_col={item['universe_col'] or '-'} | "
        f"profile_col={item['profile_col'] or '-'}"
    )

all_dates = sorted({
    d
    for item in csv_candidates
    for d in item["dates"]
    if re.fullmatch(r"20\d{2}-\d{2}-\d{2}", d)
})

print()
print("=== JSON/JSONL POSSIBLE RANK HISTORY ===")
print(f"JSON_CANDIDATE_COUNT={len(json_candidates)}")
for p in json_candidates[:30]:
    print(f"JSON={p.relative_to(root)}")

print()
print("=== FEASIBILITY ===")
print(f"DISTINCT_CSV_SNAPSHOT_DATES={len(all_dates)}")
if all_dates:
    print("CSV_SNAPSHOT_DATES=" + " | ".join(all_dates[-20:]))

if len(all_dates) >= 6:
    print("BACKFILL_FEASIBILITY=LIKELY_YES")
    print(
        "NEXT=PROVE_ROW_SEMANTICS_AND_UNIVERSE_PROFILE_COMPARABILITY_THEN_DRY_RUN_BACKFILL"
    )
elif csv_candidates or json_candidates:
    print("BACKFILL_FEASIBILITY=PARTIAL")
    print(
        "NEXT=INSPECT_CANDIDATE_FILES_AND_PROVE_AT_LEAST_6_COMPARABLE_SESSION_SNAPSHOTS"
    )
else:
    print("BACKFILL_FEASIBILITY=NO_LOCAL_STRUCTURED_RANK_SNAPSHOTS_PROVEN")
    print(
        "NEXT=DO_NOT_RELAX_TRAJECTORY_RULE;USE_EXISTING_BATCH_HISTORICAL_REPLAY_SEAM_OR_WAIT"
    )

print(f"READ_ERRORS={len(errors)}")
for p, err in errors[:10]:
    try:
        rel = p.relative_to(root)
    except ValueError:
        rel = p
    print(f"READ_ERROR={rel}::{err}")

print("BACKFILL_FEASIBILITY_CHECK=PASS")
'@

    [System.IO.File]::WriteAllText(
        $tmp,
        $code,
        (New-Object System.Text.UTF8Encoding($false))
    )

    & $Python $tmp $ProjectRoot
    if ($LASTEXITCODE -ne 0) {
        throw "BACKFILL_FEASIBILITY_CHECK_FAIL"
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
