param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$UniverseModule = Join-Path $ProjectRoot "backend\app\analysis\bist_universe.py"

foreach ($p in @($Python,$UniverseModule)) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "REQUIRED_PATH_MISSING=$p"
    }
}

$oldPythonPath = $env:PYTHONPATH
$tmp = Join-Path $env:TEMP "hisse_daily10_historical_universe_snapshot_proof_v1.py"

try {
    Write-Host "=== HISSE ROBOTU — HISTORICAL UNIVERSE SNAPSHOT PROOF V1 ==="
    Write-Host "MODE=READ_ONLY"
    Write-Host "PRODUCTION_MUTATION=NO"
    Write-Host "GOAL=PROVE_LOCAL_ASOF_BIST_UNIVERSE_INPUT"

    $env:PYTHONPATH = if ([string]::IsNullOrWhiteSpace($oldPythonPath)) {
        $ProjectRoot
    } else {
        "$ProjectRoot;$oldPythonPath"
    }

    $code = @'
from __future__ import annotations

import csv
import hashlib
import re
import sys
from collections import defaultdict
from io import StringIO
from pathlib import Path

from backend.app.analysis.bist_universe import (
    BistUniverseRepository,
    bist_bilesen_csvsini_ayristir,
)

root = Path(sys.argv[1])

skip_parts = {
    ".git", ".venv", "__pycache__", "node_modules", ".pytest_cache",
}

name_patterns = (
    "bist_endeks_bilesenleri",
    "hisse_endeks_ds",
)

def rel(path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)

def classify(path: Path) -> str:
    parts = {p.lower() for p in path.parts}
    s = str(path).lower()
    if "resources" in parts:
        return "PACKAGED_RESOURCE"
    if "cache" in parts:
        return "LIVE_CACHE"
    if "_rollback" in parts or "backup" in s:
        return "BACKUP_OR_ROLLBACK"
    if re.search(r"sprint[-_ ]?\d+", s, flags=re.I):
        return "SPRINT_SNAPSHOT"
    return "OTHER_LOCAL"

def csv_dates(raw: bytes) -> tuple[str, ...]:
    text = raw.decode("utf-8-sig", errors="replace")
    dates = set()
    for row in csv.reader(StringIO(text), delimiter=";"):
        if len(row) < 6:
            continue
        value = row[5].strip()
        if re.fullmatch(r"\d{2}/\d{2}/20\d{2}", value):
            dd, mm, yyyy = value.split("/")
            dates.add(f"{yyyy}-{mm}-{dd}")
    return tuple(sorted(dates))

files = []
for path in root.rglob("*.csv"):
    if any(part in skip_parts for part in path.parts):
        continue
    low = path.name.lower()
    if not any(pattern in low for pattern in name_patterns):
        continue
    files.append(path)

print(f"RAW_CANDIDATE_FILE_COUNT={len(files)}")

by_sha = {}
read_errors = []
for path in files:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        read_errors.append((path, exc))
        continue

    sha = hashlib.sha256(raw).hexdigest()
    if sha not in by_sha:
        by_sha[sha] = {
            "sha": sha,
            "raw": raw,
            "paths": [],
        }
    by_sha[sha]["paths"].append(path)

print(f"UNIQUE_CONTENT_COUNT={len(by_sha)}")
print()

valid = []
invalid = []

for item in by_sha.values():
    raw = item["raw"]
    paths = item["paths"]
    dates = csv_dates(raw)

    try:
        universe = bist_bilesen_csvsini_ayristir(
            raw,
            evren_adi="BIST Tüm",
            endeks_kodu="XUTUM",
            kaynak="Historical Universe Snapshot Proof",
            resmi_kaynaktan_guncel=False,
        )
    except Exception as exc:
        invalid.append((paths, dates, exc))
        continue

    valid.append(
        {
            "sha": item["sha"],
            "paths": paths,
            "dates": dates,
            "universe_date": universe.tarih,
            "symbol_count": len(universe.semboller),
            "symbols": universe.semboller,
        }
    )

print("=== VALID CANONICAL XUTUM SNAPSHOTS ===")
for item in sorted(valid, key=lambda x: (x["dates"], x["sha"])):
    primary = item["paths"][0]
    aliases = len(item["paths"]) - 1
    print(
        f"SNAPSHOT date={item['universe_date']} "
        f"dates={','.join(item['dates']) if item['dates'] else '-'} "
        f"symbols={item['symbol_count']} "
        f"class={classify(primary)} "
        f"sha={item['sha'][:12]} "
        f"path={rel(primary)} "
        f"duplicate_paths={aliases}"
    )

print()
print("=== EXPLICIT SNAPSHOT INJECTION PROOF ===")
injection_pass = 0
for item in sorted(valid, key=lambda x: (x["dates"], x["sha"])):
    primary = item["paths"][0]
    impossible_cache = root / "_discovery" / "__never_use_live_cache__.csv"
    try:
        repo = BistUniverseRepository(
            snapshot_yolu=primary,
            onbellek_yolu=impossible_cache,
            indirici=lambda _url: (_ for _ in ()).throw(RuntimeError("network disabled")),
        )
        universe = repo.evreni_yukle(
            "BIST Tüm",
            internetten_guncelle=False,
        )
        same = (
            tuple(universe.semboller) == tuple(item["symbols"])
            and len(universe.semboller) == item["symbol_count"]
        )
    except Exception as exc:
        print(f"INJECTION=FAIL path={rel(primary)} error={type(exc).__name__}:{exc}")
        continue

    if same:
        injection_pass += 1
        print(
            f"INJECTION=PASS date={universe.tarih} "
            f"symbols={len(universe.semboller)} path={rel(primary)}"
        )
    else:
        print(f"INJECTION=FAIL path={rel(primary)} reason=CONTENT_MISMATCH")

distinct_dates = sorted({
    d
    for item in valid
    for d in item["dates"]
})

print()
print("=== DATE COVERAGE ===")
print(f"DISTINCT_AUTHORITATIVE_LOCAL_DATES={len(distinct_dates)}")
if distinct_dates:
    print("DATES=" + " | ".join(distinct_dates))

by_date = defaultdict(list)
for item in valid:
    for d in item["dates"]:
        by_date[d].append(item)

for d in distinct_dates:
    counts = sorted({item["symbol_count"] for item in by_date[d]})
    print(
        f"DATE={d} SNAPSHOTS={len(by_date[d])} "
        f"SYMBOL_COUNTS={','.join(map(str, counts))}"
    )

print()
print("=== AS-OF SAFETY ===")
print("POLICY=ONLY_SNAPSHOT_DATE_LE_CUT_DATE")
print("FUTURE_SNAPSHOT_FALLBACK=FORBIDDEN")
print("MISSING_ASOF_SNAPSHOT=FAIL_CLOSED")
print("CURRENT_LIVE_CACHE_AS_HISTORICAL=FORBIDDEN")

print()
print("=== FINAL HISTORICAL UNIVERSE DECISION ===")

if injection_pass == 0:
    print("HISTORICAL_UNIVERSE_INPUT=NOT_PROVEN")
    print("NEXT=DO_NOT_PATCH_REPLAY;FIX_EXPLICIT_SNAPSHOT_INJECTION_PROOF")
elif len(distinct_dates) >= 6:
    print("HISTORICAL_UNIVERSE_INPUT=PROVEN_LOCAL_MULTISESSION")
    print(
        "NEXT=BUILD_READ_ONLY_ASOF_SNAPSHOT_SELECTOR_AND_6_SESSION_CANONICAL_REPLAY_DRY_RUN"
    )
elif len(distinct_dates) >= 2:
    print("HISTORICAL_UNIVERSE_INPUT=PROVEN_BUT_COVERAGE_PARTIAL")
    print(
        "NEXT=DO_NOT_USE_FUTURE_UNIVERSE;CHECK_TARGET_SESSION_COVERAGE_AND_ARCHIVE_SOURCE"
    )
elif len(distinct_dates) == 1:
    print("HISTORICAL_UNIVERSE_INPUT=SINGLE_SNAPSHOT_ONLY")
    print(
        "NEXT=DO_NOT_BACKFILL_5S;START_DAILY_APPEND_ONLY_UNIVERSE_SNAPSHOTS_OR_SOURCE_ARCHIVE"
    )
else:
    print("HISTORICAL_UNIVERSE_INPUT=NO_DATED_XUTUM_SNAPSHOT")
    print("NEXT=DO_NOT_BACKFILL_5S;SOURCE_AUTHORITATIVE_HISTORICAL_UNIVERSE")

print(f"INVALID_UNIQUE_CONTENT={len(invalid)}")
print(f"READ_ERRORS={len(read_errors)}")
print("HISTORICAL_UNIVERSE_SNAPSHOT_PROOF=PASS")
'@

    [System.IO.File]::WriteAllText(
        $tmp,
        $code,
        (New-Object System.Text.UTF8Encoding($false))
    )

    & $Python $tmp $ProjectRoot
    if ($LASTEXITCODE -ne 0) {
        throw "HISTORICAL_UNIVERSE_SNAPSHOT_PROOF_FAIL"
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
