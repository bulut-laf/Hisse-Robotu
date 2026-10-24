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
$tmp = Join-Path $env:TEMP "hisse_daily10_xutum_change_ledger_reconcile_v1.py"

try {
    Write-Host "=== HISSE ROBOTU — XUTUM CHANGE LEDGER RECONCILIATION V1 ==="
    Write-Host "MODE=READ_ONLY"
    Write-Host "PRODUCTION_MUTATION=NO"
    Write-Host "GOAL=RECONSTRUCT_18_TO_25_AUG_UNIVERSE_FROM_OFFICIAL_EFFECTIVE_CHANGES"

    $env:PYTHONPATH = if ([string]::IsNullOrWhiteSpace($oldPythonPath)) {
        $ProjectRoot
    } else {
        "$ProjectRoot;$oldPythonPath"
    }

    $code = @'
from __future__ import annotations

import csv
import hashlib
import io
import re
import subprocess
import sys
import zipfile
from collections import defaultdict
from datetime import date
from pathlib import Path

from backend.app.analysis.bist_universe import bist_bilesen_csvsini_ayristir

root = Path(sys.argv[1])

BASELINE_DATE = date(2026, 8, 17)
TERMINAL_DATE = date(2026, 8, 25)
TARGET_DATES = (
    date(2026, 8, 18),
    date(2026, 8, 19),
    date(2026, 8, 20),
    date(2026, 8, 21),
    date(2026, 8, 24),
    date(2026, 8, 25),
)

# Official BIST/KAP effective XUTUM additions verified externally:
# 2026-08-18 CITAS  — CITLEKCI MAGAZACILIK GIDA
# 2026-08-20 TKNKA  — TEKNIKA PLASTIK
# 2026-08-20 VEYAS  — TURKER VANGOLU ENERJI
# 2026-08-21 KPEKS  — KAPEKS KIMYA
#
# This validator does NOT trust the ledger by itself. It only accepts
# reconstruction when the local canonical XUTUM snapshot diff from
# 2026-08-17 to 2026-08-25 matches this ledger exactly, with zero removals.
LEDGER = (
    (date(2026, 8, 18), "CITAS.IS"),
    (date(2026, 8, 20), "TKNKA.IS"),
    (date(2026, 8, 20), "VEYAS.IS"),
    (date(2026, 8, 21), "KPEKS.IS"),
)

TARGET_NAMES = {
    "bist_endeks_bilesenleri.csv",
    "hisse_endeks_ds.csv",
}

def rel(path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)

def parse_dates(raw: bytes) -> tuple[date, ...]:
    text = raw.decode("utf-8-sig", errors="replace")
    dates = set()
    for row in csv.reader(io.StringIO(text), delimiter=";"):
        if len(row) < 6:
            continue
        value = row[5].strip()
        if re.fullmatch(r"\d{2}/\d{2}/20\d{2}", value):
            dd, mm, yyyy = map(int, value.split("/"))
            dates.add(date(yyyy, mm, dd))
    return tuple(sorted(dates))

def parse_xutum(raw: bytes):
    return bist_bilesen_csvsini_ayristir(
        raw,
        evren_adi="BIST Tüm",
        endeks_kodu="XUTUM",
        kaynak="XUTUM Change Ledger Reconciliation",
        resmi_kaynaktan_guncel=False,
    )

records = {}

def add_raw(raw: bytes, source: str) -> None:
    sha = hashlib.sha256(raw).hexdigest()
    rec = records.setdefault(sha, {"raw": raw, "sources": []})
    rec["sources"].append(source)

# Working tree, including backups/rollback.
for path in root.rglob("*.csv"):
    if ".venv" in path.parts or ".git" in path.parts:
        continue
    low = path.name.lower()
    if low not in TARGET_NAMES and not any(
        token in low
        for token in ("bist_endeks_bilesenleri", "hisse_endeks_ds")
    ):
        continue
    try:
        add_raw(path.read_bytes(), f"file:{rel(path)}")
    except OSError:
        pass

# ZIP archives.
for zpath in root.rglob("*.zip"):
    if ".venv" in zpath.parts or ".git" in zpath.parts:
        continue
    try:
        with zipfile.ZipFile(zpath, "r") as zf:
            for name in zf.namelist():
                base = Path(name).name.lower()
                if base not in TARGET_NAMES and not any(
                    token in base
                    for token in ("bist_endeks_bilesenleri", "hisse_endeks_ds")
                ):
                    continue
                try:
                    add_raw(zf.read(name), f"zip:{rel(zpath)}::{name}")
                except KeyError:
                    pass
    except (OSError, zipfile.BadZipFile):
        pass

# Git history.
try:
    probe = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    git_ok = probe.returncode == 0 and probe.stdout.strip() == b"true"
except OSError:
    git_ok = False

if git_ok:
    for repo_path in (
        "backend/cache/bist_endeks_bilesenleri.csv",
        "backend/resources/bist_endeks_bilesenleri.csv",
    ):
        revs = subprocess.run(
            ["git", "rev-list", "--all", "--", repo_path],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if revs.returncode != 0:
            continue
        for commit in revs.stdout.decode("ascii", errors="ignore").splitlines():
            if not commit:
                continue
            shown = subprocess.run(
                ["git", "show", f"{commit}:{repo_path}"],
                cwd=root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if shown.returncode == 0 and shown.stdout:
                add_raw(shown.stdout, f"git:{commit[:12]}:{repo_path}")

snapshots = []
for sha, rec in records.items():
    try:
        dates = parse_dates(rec["raw"])
        universe = parse_xutum(rec["raw"])
    except Exception:
        continue
    if not dates:
        continue
    snapshots.append(
        {
            "date": max(dates),
            "symbols": frozenset(universe.semboller),
            "count": len(universe.semboller),
            "sha": sha,
            "sources": tuple(rec["sources"]),
        }
    )

by_date = defaultdict(list)
for item in snapshots:
    by_date[item["date"]].append(item)

def best_for(d: date):
    items = by_date.get(d, ())
    if not items:
        return None
    return sorted(
        items,
        key=lambda x: (len(x["sources"]), x["count"]),
        reverse=True,
    )[0]

baseline = best_for(BASELINE_DATE)
terminal = best_for(TERMINAL_DATE)

print("=== REQUIRED ANCHORS ===")
print(f"BASELINE_2026_08_17={'FOUND' if baseline else 'MISSING'}")
if baseline:
    print(
        f"BASELINE symbols={baseline['count']} sha={baseline['sha'][:12]} "
        f"primary={baseline['sources'][0]}"
    )

print(f"TERMINAL_2026_08_25={'FOUND' if terminal else 'MISSING'}")
if terminal:
    print(
        f"TERMINAL symbols={terminal['count']} sha={terminal['sha'][:12]} "
        f"primary={terminal['sources'][0]}"
    )

print()
print("=== OFFICIAL XUTUM CHANGE LEDGER ===")
for effective, symbol in LEDGER:
    print(f"{effective.isoformat()} ADD {symbol}")

expected_added = {symbol for _effective, symbol in LEDGER}

print()
print("=== ANCHOR DIFF RECONCILIATION ===")
if baseline and terminal:
    actual_added = terminal["symbols"] - baseline["symbols"]
    actual_removed = baseline["symbols"] - terminal["symbols"]

    print(f"ACTUAL_ADDED_COUNT={len(actual_added)}")
    print("ACTUAL_ADDED=" + (",".join(sorted(actual_added)) or "NONE"))
    print(f"ACTUAL_REMOVED_COUNT={len(actual_removed)}")
    print("ACTUAL_REMOVED=" + (",".join(sorted(actual_removed)) or "NONE"))
    print(f"EXPECTED_ADDED_COUNT={len(expected_added)}")
    print("EXPECTED_ADDED=" + ",".join(sorted(expected_added)))

    ledger_exact = actual_added == expected_added and not actual_removed
    print(f"LEDGER_EXACT_MATCH={'YES' if ledger_exact else 'NO'}")
else:
    actual_added = set()
    actual_removed = set()
    ledger_exact = False
    print("LEDGER_EXACT_MATCH=NO")
    print("REASON=MISSING_REQUIRED_ANCHOR")

print()
print("=== RECONSTRUCTED TARGET UNIVERSES ===")
if baseline and ledger_exact:
    current = set(baseline["symbols"])
    ledger_by_date = defaultdict(list)
    for effective, symbol in LEDGER:
        ledger_by_date[effective].append(symbol)

    for target in TARGET_DATES:
        for effective in sorted(ledger_by_date):
            if effective == target:
                current.update(ledger_by_date[effective])
        exact = best_for(target)
        exact_match = (
            exact is not None and frozenset(current) == exact["symbols"]
        )
        print(
            f"DATE={target.isoformat()} symbols={len(current)} "
            f"direct_snapshot={'YES' if exact else 'NO'} "
            f"direct_match={'YES' if exact_match else ('N/A' if exact is None else 'NO')}"
        )
else:
    print("RECONSTRUCTION=SKIPPED")

print()
print("=== FINAL CHANGE-LEDGER DECISION ===")
if not baseline:
    print("XUTUM_LEDGER_RECONCILIATION=BLOCKED_BASELINE_17_MISSING")
    print("NEXT=SOURCE_EXACT_2026_08_17_XUTUM_SNAPSHOT")
elif not terminal:
    print("XUTUM_LEDGER_RECONCILIATION=BLOCKED_TERMINAL_25_MISSING")
    print("NEXT=SOURCE_EXACT_2026_08_25_XUTUM_SNAPSHOT")
elif actual_removed:
    print("XUTUM_LEDGER_RECONCILIATION=FAIL_REMOVALS_NOT_IN_LEDGER")
    print("NEXT=SOURCE_OFFICIAL_REMOVAL_ANNOUNCEMENTS")
elif actual_added != expected_added:
    print("XUTUM_LEDGER_RECONCILIATION=FAIL_DIFF_MISMATCH")
    print("NEXT=RECONCILE_UNACCOUNTED_XUTUM_CHANGES_BEFORE_REPLAY")
else:
    print("XUTUM_LEDGER_RECONCILIATION=PROVEN")
    print(
        "NEXT=BUILD_6_SESSION_READ_ONLY_CANONICAL_RESEARCH_REPLAY_USING_RECONSTRUCTED_UNIVERSES"
    )

print("XUTUM_CHANGE_LEDGER_RECONCILIATION=PASS")
'@

    [System.IO.File]::WriteAllText(
        $tmp,
        $code,
        (New-Object System.Text.UTF8Encoding($false))
    )

    & $Python $tmp $ProjectRoot
    if ($LASTEXITCODE -ne 0) {
        throw "XUTUM_CHANGE_LEDGER_RECONCILIATION_FAIL"
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
