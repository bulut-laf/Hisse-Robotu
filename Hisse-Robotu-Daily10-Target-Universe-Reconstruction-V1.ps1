param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$UniverseModule = Join-Path $ProjectRoot "backend\app\analysis\bist_universe.py"

foreach ($p in @($Python, $UniverseModule)) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "REQUIRED_PATH_MISSING=$p"
    }
}

$oldPythonPath = $env:PYTHONPATH
$tmp = Join-Path $env:TEMP "hisse_daily10_target_universe_reconstruction_v1.py"

try {
    Write-Host "=== HISSE ROBOTU — TARGET UNIVERSE RECONSTRUCTION V1 ==="
    Write-Host "MODE=READ_ONLY"
    Write-Host "PRODUCTION_MUTATION=NO"
    Write-Host "GOAL=RECONCILE_EXACT_17_AUG_BASELINE_TO_25_AUG_AND_BUILD_6_TARGET_UNIVERSES"

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
import os
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
BASELINE_SHA = "04017af0e22aefd23b02f75cc96fa71a4f80b5c1dc6ee661dd57f1052e4712ef"

TARGET_DATES = (
    date(2026, 8, 18),
    date(2026, 8, 19),
    date(2026, 8, 20),
    date(2026, 8, 21),
    date(2026, 8, 24),
    date(2026, 8, 25),
)

# Previously established effective XUTUM additions for the target window.
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

def parse_xutum(raw: bytes, source: str):
    return bist_bilesen_csvsini_ayristir(
        raw,
        evren_adi="BIST Tüm",
        endeks_kodu="XUTUM",
        kaynak=source,
        resmi_kaynaktan_guncel=False,
    )

def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

records: dict[str, dict[str, object]] = {}

def add_raw(raw: bytes, source: str) -> None:
    sha = digest(raw)
    rec = records.setdefault(
        sha,
        {"raw": raw, "sources": []},
    )
    rec["sources"].append(source)

# Search roots: project, parent, common user folders.
userprofile = Path(os.environ.get("USERPROFILE", ""))
temp = Path(os.environ.get("TEMP", ""))

roots = []
for p in (
    root,
    root.parent,
    userprofile / "Downloads",
    userprofile / "Desktop",
    userprofile / "Documents",
    userprofile / "OneDrive",
    temp,
):
    if p and p.exists():
        try:
            rp = p.resolve()
        except OSError:
            rp = p
        if rp not in roots:
            roots.append(rp)

skip_names = {
    ".git", ".venv", "node_modules", "__pycache__",
    ".pytest_cache", "AppData", "$Recycle.Bin",
}

def walk_files(base: Path):
    stack = [base]
    while stack:
        current = stack.pop()
        try:
            entries = list(current.iterdir())
        except (OSError, PermissionError):
            continue
        for entry in entries:
            try:
                if entry.is_dir():
                    if entry.name in skip_names:
                        continue
                    stack.append(entry)
                    continue
            except OSError:
                continue
            yield entry

seen_paths = set()
for base in roots:
    for path in walk_files(base):
        try:
            key = str(path.resolve())
        except OSError:
            key = str(path)
        if key in seen_paths:
            continue
        seen_paths.add(key)

        low = path.name.lower()
        suffix = path.suffix.lower()

        if suffix == ".csv" and (
            low in TARGET_NAMES
            or any(tok in low for tok in ("bist_endeks_bilesenleri", "hisse_endeks_ds"))
        ):
            try:
                add_raw(path.read_bytes(), f"FILE::{path}")
            except (OSError, PermissionError):
                pass
            continue

        if suffix == ".zip":
            try:
                with zipfile.ZipFile(path, "r") as zf:
                    for name in zf.namelist():
                        base_name = Path(name).name.lower()
                        if not (
                            base_name.endswith(".csv")
                            and (
                                base_name in TARGET_NAMES
                                or any(
                                    tok in base_name
                                    for tok in ("bist_endeks_bilesenleri", "hisse_endeks_ds")
                                )
                            )
                        ):
                            continue
                        try:
                            add_raw(zf.read(name), f"ZIP::{path}::{name}")
                        except (KeyError, RuntimeError):
                            pass
            except (OSError, PermissionError, zipfile.BadZipFile):
                pass

# Git object history inside repo.
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
                add_raw(shown.stdout, f"GIT::{commit[:12]}::{repo_path}")

snapshots = []
for sha, rec in records.items():
    raw = rec["raw"]
    try:
        dates = parse_dates(raw)
        universe = parse_xutum(raw, f"snapshot:{sha[:12]}")
    except Exception:
        continue

    if not dates:
        continue

    snapshots.append(
        {
            "sha": sha,
            "raw": raw,
            "sources": tuple(rec["sources"]),
            "date": max(dates),
            "symbols": frozenset(universe.semboller),
            "count": len(universe.semboller),
        }
    )

baseline_candidates = [x for x in snapshots if x["sha"] == BASELINE_SHA]
terminal_candidates = [x for x in snapshots if x["date"] == TERMINAL_DATE]

baseline = baseline_candidates[0] if baseline_candidates else None
terminal = None
if terminal_candidates:
    terminal = sorted(
        terminal_candidates,
        key=lambda x: (len(x["sources"]), x["count"]),
        reverse=True,
    )[0]

print()
print("=== EXACT ANCHORS ===")
print(f"BASELINE_EXACT_SHA={'FOUND' if baseline else 'MISSING'}")
if baseline:
    print(
        f"BASELINE date={baseline['date'].isoformat()} "
        f"symbols={baseline['count']} sha={baseline['sha']} "
        f"source={baseline['sources'][0]}"
    )

print(f"TERMINAL_2026_08_25={'FOUND' if terminal else 'MISSING'}")
if terminal:
    print(
        f"TERMINAL date={terminal['date'].isoformat()} "
        f"symbols={terminal['count']} sha={terminal['sha']} "
        f"source={terminal['sources'][0]}"
    )

print()
print("=== 17 -> 25 CANONICAL XUTUM DIFF ===")

expected_added = {symbol for _d, symbol in LEDGER}

if baseline and terminal:
    actual_added = terminal["symbols"] - baseline["symbols"]
    actual_removed = baseline["symbols"] - terminal["symbols"]

    print(f"ACTUAL_ADDED_COUNT={len(actual_added)}")
    print("ACTUAL_ADDED=" + (",".join(sorted(actual_added)) or "NONE"))
    print(f"ACTUAL_REMOVED_COUNT={len(actual_removed)}")
    print("ACTUAL_REMOVED=" + (",".join(sorted(actual_removed)) or "NONE"))
    print(f"EXPECTED_ADDED_COUNT={len(expected_added)}")
    print("EXPECTED_ADDED=" + ",".join(sorted(expected_added)))

    exact_reconcile = (
        actual_added == expected_added
        and not actual_removed
    )
else:
    actual_added = set()
    actual_removed = set()
    exact_reconcile = False

print(f"LEDGER_EXACT_MATCH={'YES' if exact_reconcile else 'NO'}")

print()
print("=== RECONSTRUCTED TARGET UNIVERSES ===")

reconstructed = {}
if baseline and exact_reconcile:
    current = set(baseline["symbols"])
    by_effective = defaultdict(list)
    for effective, symbol in LEDGER:
        by_effective[effective].append(symbol)

    for target in TARGET_DATES:
        for symbol in by_effective.get(target, ()):
            current.add(symbol)
        reconstructed[target] = frozenset(current)

        direct = [
            x for x in snapshots
            if x["date"] == target
        ]
        direct_best = (
            sorted(
                direct,
                key=lambda x: (len(x["sources"]), x["count"]),
                reverse=True,
            )[0]
            if direct
            else None
        )

        if direct_best is None:
            direct_status = "NONE"
        else:
            direct_status = (
                "MATCH"
                if direct_best["symbols"] == reconstructed[target]
                else "MISMATCH"
            )

        print(
            f"DATE={target.isoformat()} "
            f"symbols={len(reconstructed[target])} "
            f"direct_snapshot={direct_status}"
        )

print()
print("=== TARGET UNIVERSE INTEGRITY ===")

if reconstructed:
    counts = [len(reconstructed[d]) for d in TARGET_DATES]
    print("SYMBOL_COUNTS=" + " -> ".join(map(str, counts)))

    expected_counts = []
    c = baseline["count"]
    expected_counts.append(c + 1)  # 18: CITAS
    expected_counts.append(c + 1)  # 19: unchanged
    expected_counts.append(c + 3)  # 20: +TKNKA +VEYAS
    expected_counts.append(c + 4)  # 21: +KPEKS
    expected_counts.append(c + 4)  # 24: unchanged
    expected_counts.append(c + 4)  # 25: terminal

    print("EXPECTED_COUNTS=" + " -> ".join(map(str, expected_counts)))
    counts_match = counts == expected_counts
    print(f"COUNT_PATH_MATCH={'YES' if counts_match else 'NO'}")

    terminal_match = (
        reconstructed[TERMINAL_DATE] == terminal["symbols"]
        if terminal
        else False
    )
    print(f"RECONSTRUCTED_25_EQUALS_TERMINAL={'YES' if terminal_match else 'NO'}")
else:
    counts_match = False
    terminal_match = False
    print("RECONSTRUCTED=NONE")

print()
print("=== FINAL TARGET UNIVERSE DECISION ===")

if not baseline:
    print("TARGET_UNIVERSES_RECONSTRUCTION=BLOCKED_BASELINE_MISSING")
    print("NEXT=DO_NOT_REPLAY")
elif not terminal:
    print("TARGET_UNIVERSES_RECONSTRUCTION=BLOCKED_TERMINAL_MISSING")
    print("NEXT=DO_NOT_REPLAY")
elif actual_removed:
    print("TARGET_UNIVERSES_RECONSTRUCTION=FAIL_UNACCOUNTED_REMOVALS")
    print("NEXT=SOURCE_OFFICIAL_REMOVAL_EFFECTIVE_DATES")
elif actual_added != expected_added:
    print("TARGET_UNIVERSES_RECONSTRUCTION=FAIL_ADDITION_DIFF_MISMATCH")
    print("NEXT=RECONCILE_UNACCOUNTED_XUTUM_CHANGES")
elif not counts_match or not terminal_match:
    print("TARGET_UNIVERSES_RECONSTRUCTION=FAIL_INTEGRITY")
    print("NEXT=DO_NOT_REPLAY")
else:
    print("TARGET_UNIVERSES_RECONSTRUCTION=PROVEN")
    print(
        "NEXT=BUILD_MINIMAL_OPT_IN_CANONICAL_CUTDATE_REPLAY_ADAPTER_AND_RUN_6_SESSION_READ_ONLY_DRY_RUN"
    )

print("TARGET_UNIVERSE_RECONSTRUCTION_CHECK=PASS")
'@

    [System.IO.File]::WriteAllText(
        $tmp,
        $code,
        (New-Object System.Text.UTF8Encoding($false))
    )

    & $Python $tmp $ProjectRoot
    if ($LASTEXITCODE -ne 0) {
        throw "TARGET_UNIVERSE_RECONSTRUCTION_CHECK_FAIL"
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
