param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu",
    [string]$AsOf = "2026-08-25",
    [int]$Sessions = 6
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
$tmp = Join-Path $env:TEMP "hisse_daily10_universe_archive_coverage_v1.py"

try {
    Write-Host "=== HISSE ROBOTU — UNIVERSE ARCHIVE COVERAGE V1 FIX1 ==="
    Write-Host "MODE=READ_ONLY"
    Write-Host "PRODUCTION_MUTATION=NO"
    Write-Host ("AS_OF=" + $AsOf)
    Write-Host ("TARGET_SESSIONS=" + $Sessions)
    Write-Host "GOAL=PROVE_TARGET_SESSION_UNIVERSE_COVERAGE_FROM_LOCAL_ARCHIVES"

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
from datetime import date, timedelta
from pathlib import Path

from backend.app.analysis.bist_universe import (
    bist_bilesen_csvsini_ayristir,
)

root = Path(sys.argv[1])
as_of = date.fromisoformat(sys.argv[2])
session_count = int(sys.argv[3])

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

def canonical_xutum(raw: bytes):
    return bist_bilesen_csvsini_ayristir(
        raw,
        evren_adi="BIST Tüm",
        endeks_kodu="XUTUM",
        kaynak="Archive Coverage Proof",
        resmi_kaynaktan_guncel=False,
    )

def source_class(source: str) -> str:
    s = source.lower()
    if s.startswith("git:"):
        return "GIT_HISTORY"
    if s.startswith("zip:"):
        return "ZIP_ARCHIVE"
    if "_rollback" in s:
        return "ROLLBACK"
    if "backup" in s or "yedek" in s:
        return "BACKUP"
    normalized = s.replace("\\", "/")
    if "/cache/" in normalized:
        return "CACHE"
    if "/resources/" in normalized:
        return "RESOURCE"
    return "LOCAL_FILE"

records_by_sha = {}

def add_raw(raw: bytes, source: str) -> None:
    sha = hashlib.sha256(raw).hexdigest()
    rec = records_by_sha.setdefault(
        sha,
        {"sha": sha, "raw": raw, "sources": []},
    )
    rec["sources"].append(source)

# 1) Entire working tree, INCLUDING rollback/backup this time.
for path in root.rglob("*.csv"):
    low_name = path.name.lower()
    if low_name not in TARGET_NAMES and not any(
        token in low_name
        for token in ("bist_endeks_bilesenleri", "hisse_endeks_ds")
    ):
        continue
    if ".venv" in path.parts or ".git" in path.parts:
        continue
    try:
        add_raw(path.read_bytes(), f"file:{rel(path)}")
    except OSError:
        pass

# 2) ZIP archives anywhere in repo.
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

# 3) Git object history if available.
git_available = False
git_revisions = 0
try:
    probe = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    git_available = probe.returncode == 0 and probe.stdout.strip() == b"true"
except OSError:
    git_available = False

git_paths = (
    "backend/cache/bist_endeks_bilesenleri.csv",
    "backend/resources/bist_endeks_bilesenleri.csv",
)

if git_available:
    for repo_path in git_paths:
        revs = subprocess.run(
            ["git", "rev-list", "--all", "--", repo_path],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if revs.returncode != 0:
            continue
        commits = [x for x in revs.stdout.decode("ascii", errors="ignore").splitlines() if x]
        for commit in commits:
            shown = subprocess.run(
                ["git", "show", f"{commit}:{repo_path}"],
                cwd=root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if shown.returncode != 0 or not shown.stdout:
                continue
            git_revisions += 1
            add_raw(shown.stdout, f"git:{commit[:12]}:{repo_path}")

valid = []
invalid = 0
for rec in records_by_sha.values():
    raw = rec["raw"]
    try:
        dates = parse_dates(raw)
        universe = canonical_xutum(raw)
    except Exception:
        invalid += 1
        continue

    if not dates:
        continue

    valid.append(
        {
            "sha": rec["sha"],
            "sources": tuple(rec["sources"]),
            "dates": dates,
            "snapshot_date": max(dates),
            "symbols": frozenset(universe.semboller),
            "symbol_count": len(universe.semboller),
        }
    )

valid.sort(key=lambda x: (x["snapshot_date"], x["sha"]))

print(f"GIT_AVAILABLE={'YES' if git_available else 'NO'}")
print(f"GIT_FILE_REVISIONS_READ={git_revisions}")
print(f"UNIQUE_RAW_CONTENT={len(records_by_sha)}")
print(f"VALID_XUTUM_SNAPSHOTS={len(valid)}")
print(f"INVALID_CONTENT={invalid}")
print()

print("=== DISCOVERED AUTHORITATIVE SNAPSHOTS ===")
for item in valid:
    source = item["sources"][0]
    print(
        f"SNAPSHOT={item['snapshot_date'].isoformat()} "
        f"symbols={item['symbol_count']} "
        f"sha={item['sha'][:12]} "
        f"class={source_class(source)} "
        f"sources={len(item['sources'])} "
        f"primary={source}"
    )

# Weekday targets are only a candidate session calendar; this script does not
# silently claim they are exchange-open days.
targets = []
cursor = as_of
while len(targets) < session_count:
    if cursor.weekday() < 5:
        targets.append(cursor)
    cursor -= timedelta(days=1)
targets = sorted(targets)

print()
print("=== TARGET WINDOW ===")
print("TARGET_CALENDAR=WEEKDAY_CANDIDATES_ONLY")
print("TARGETS=" + " | ".join(d.isoformat() for d in targets))

# Deduplicate by snapshot_date and prefer the copy with most sources, then symbols.
by_date = defaultdict(list)
for item in valid:
    by_date[item["snapshot_date"]].append(item)

date_items = {}
for d, items in by_date.items():
    date_items[d] = sorted(
        items,
        key=lambda x: (len(x["sources"]), x["symbol_count"]),
        reverse=True,
    )[0]

snapshot_dates = sorted(date_items)

def prior(d: date):
    candidates = [x for x in snapshot_dates if x <= d]
    return date_items[max(candidates)] if candidates else None

def next_after(d: date):
    candidates = [x for x in snapshot_dates if x >= d]
    return date_items[min(candidates)] if candidates else None

coverage_rows = []
for target in targets:
    exact = date_items.get(target)
    if exact:
        coverage_rows.append((target, "EXACT", exact, exact))
        continue

    p = prior(target)
    n = next_after(target)

    if p and n and p["snapshot_date"] < target < n["snapshot_date"]:
        if p["symbols"] == n["symbols"]:
            coverage_rows.append((target, "BRACKETED_IDENTICAL", p, n))
        else:
            coverage_rows.append((target, "BRACKETED_CHANGED", p, n))
    elif p:
        coverage_rows.append((target, "PRIOR_ONLY", p, None))
    else:
        coverage_rows.append((target, "NO_PRIOR", None, n))

print()
print("=== TARGET SESSION COVERAGE ===")
for target, status, p, n in coverage_rows:
    ptxt = p["snapshot_date"].isoformat() if p else "-"
    ntxt = n["snapshot_date"].isoformat() if n else "-"
    detail = ""
    if p and n and p is not n:
        added = len(n["symbols"] - p["symbols"])
        removed = len(p["symbols"] - n["symbols"])
        detail = f" added={added} removed={removed}"
    print(
        f"DATE={target.isoformat()} status={status} "
        f"prior={ptxt} next={ntxt}{detail}"
    )

print()
print("=== CONSECUTIVE SNAPSHOT DIFFS ===")
for left_date, right_date in zip(snapshot_dates, snapshot_dates[1:]):
    left = date_items[left_date]
    right = date_items[right_date]
    added = right["symbols"] - left["symbols"]
    removed = left["symbols"] - right["symbols"]
    print(
        f"{left_date.isoformat()}->{right_date.isoformat()} "
        f"added={len(added)} removed={len(removed)} "
        f"same={'YES' if not added and not removed else 'NO'}"
    )
    if added:
        print("  ADDED=" + ",".join(sorted(added)[:30]))
    if removed:
        print("  REMOVED=" + ",".join(sorted(removed)[:30]))

statuses = [row[1] for row in coverage_rows]

print()
print("=== FINAL TARGET COVERAGE DECISION ===")
if statuses and all(s in {"EXACT", "BRACKETED_IDENTICAL"} for s in statuses):
    print("TARGET_UNIVERSE_COVERAGE=PROVEN_FOR_WEEKDAY_WINDOW")
    print(
        "NEXT=VERIFY_EXCHANGE_SESSION_DATES_THEN_BUILD_6_SESSION_READ_ONLY_CANONICAL_REPLAY"
    )
elif any(s == "BRACKETED_CHANGED" for s in statuses):
    print("TARGET_UNIVERSE_COVERAGE=NOT_PROVEN_MEMBERSHIP_CHANGED")
    print(
        "NEXT=SOURCE_MISSING_INTERMEDIATE_OFFICIAL_SNAPSHOTS;DO_NOT_INTERPOLATE_CHANGED_INTERVAL"
    )
elif all(s != "NO_PRIOR" for s in statuses):
    print("TARGET_UNIVERSE_COVERAGE=PRIOR_SNAPSHOT_ONLY")
    print(
        "NEXT=NEED_VALIDITY_BRACKET_OR_ARCHIVE_CONFIRMATION;DO_NOT_ASSUME_PRIOR_SNAPSHOT_STAYED_VALID"
    )
else:
    print("TARGET_UNIVERSE_COVERAGE=GAP")
    print(
        "NEXT=SEARCH_EXTERNAL_OR_OFFLINE_AUTHORITATIVE_ARCHIVE;DO_NOT_BACKFILL"
    )

print("UNIVERSE_ARCHIVE_COVERAGE_FIX1=PASS")
'@

    [System.IO.File]::WriteAllText(
        $tmp,
        $code,
        (New-Object System.Text.UTF8Encoding($false))
    )

    & $Python $tmp $ProjectRoot $AsOf $Sessions
    if ($LASTEXITCODE -ne 0) {
        throw "UNIVERSE_ARCHIVE_COVERAGE_FAIL"
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
