param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Adapter = Join-Path $ProjectRoot "backend\app\analysis\historical_research_replay.py"
$MemoryFile = Join-Path $ProjectRoot "data\ranking_memory\rank_observations.jsonl"
$Discovery = Join-Path $ProjectRoot "_discovery"

$Required = @(
    $Python,
    $Adapter,
    (Join-Path $ProjectRoot "backend\app\analysis\bist_universe.py"),
    (Join-Path $ProjectRoot "backend\app\analysis\market_scanner.py"),
    (Join-Path $ProjectRoot "backend\app\analysis\ranking_memory.py"),
    (Join-Path $ProjectRoot "backend\app\analysis\ranking_trajectory.py"),
    (Join-Path $ProjectRoot "backend\app\analysis\daily_early_trajectory.py")
)

foreach ($p in $Required) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "REQUIRED_PATH_MISSING=$p"
    }
}

New-Item -ItemType Directory -Path $Discovery -Force | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$report = Join-Path $Discovery "Hisse-Robotu-Daily10-PostIntegration-6Session-Acceptance-V1-FIX1-$stamp.txt"

$oldPythonPath = $env:PYTHONPATH
$tmp = Join-Path $env:TEMP "hisse_daily10_postintegration_6session_acceptance_v1.py"

try {
    Write-Host "=== HISSE ROBOTU — POST-INTEGRATION 6-SESSION ACCEPTANCE V1 FIX1 ==="
    Write-Host "MODE=READ_ONLY"
    Write-Host "PRODUCTION_MUTATION=NO"
    Write-Host "RANKING_MEMORY_WRITE=DISABLED"
    Write-Host "TARGET=REPO_HISTORICAL_RESEARCH_REPLAY_ADAPTER"
    Write-Host "SESSIONS=2026-08-18,19,20,21,24,25"

    $env:PYTHONPATH = if ([string]::IsNullOrWhiteSpace($oldPythonPath)) {
        $ProjectRoot
    } else {
        "$ProjectRoot;$oldPythonPath"
    }

    $code = @'
from __future__ import annotations

import csv
import hashlib
import inspect
import io
import os
import re
import subprocess
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

root = Path(sys.argv[1])

from backend.app.analysis.bist_universe import bist_bilesen_csvsini_ayristir
from backend.app.analysis.historical_research_replay import (
    HISTORICAL_REPLAY_UNIVERSE_SOURCE,
    replay_canonical_research,
)
import backend.app.analysis.historical_research_replay as replay_module
from backend.app.analysis.market_scanner import MarketScanRequest
from backend.app.analysis.ranking_memory import RankObservationJsonlStore
from backend.app.analysis.ranking_trajectory import build_rank_trajectories
from backend.app.analysis.daily_early_trajectory import (
    build_daily_early_trajectory_candidates,
    daily_early_trajectory_rows,
)

BASELINE_SHA = "04017af0e22aefd23b02f75cc96fa71a4f80b5c1dc6ee661dd57f1052e4712ef"
TERMINAL_DATE = date(2026, 8, 25)

TARGET_DATES = (
    date(2026, 8, 18),
    date(2026, 8, 19),
    date(2026, 8, 20),
    date(2026, 8, 21),
    date(2026, 8, 24),
    date(2026, 8, 25),
)

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

memory_path = root / "data" / "ranking_memory" / "rank_observations.jsonl"

def file_sha(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    return hashlib.sha256(path.read_bytes()).hexdigest()

memory_before = file_sha(memory_path)

adapter_source = inspect.getsource(replay_module)
if "append_snapshot(" in adapter_source:
    raise RuntimeError("ADAPTER_PERSISTENCE_GUARD_FAIL_APPEND_SNAPSHOT")
if "RankObservationJsonlStore" in adapter_source:
    raise RuntimeError("ADAPTER_PERSISTENCE_GUARD_FAIL_STORE_REFERENCE")
if "yeni teknik skor, işlem sinyali veya AL/SAT kararı üretmez" not in (
    replay_module.__doc__ or ""
):
    raise RuntimeError("ADAPTER_CONTRACT_PHRASE_MISSING")

print()
print("=== ADAPTER CONTRACT ===")
print("MODULE=backend/app/analysis/historical_research_replay.py")
print("PERSISTENCE_REFERENCE=NONE")
print("CONTRACT_PHRASE=PASS")
print("RANKING_MEMORY_SHA_BEFORE=" + memory_before)

def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

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

records: dict[str, dict[str, object]] = {}

def add_raw(raw: bytes, source: str) -> None:
    sha = digest(raw)
    rec = records.setdefault(sha, {"raw": raw, "sources": []})
    rec["sources"].append(source)

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

seen = set()
for base in roots:
    for path in walk_files(base):
        try:
            key = str(path.resolve())
        except OSError:
            key = str(path)
        if key in seen:
            continue
        seen.add(key)

        low = path.name.lower()
        suffix = path.suffix.lower()

        if suffix == ".csv" and (
            low in TARGET_NAMES
            or any(x in low for x in ("bist_endeks_bilesenleri", "hisse_endeks_ds"))
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
                                    x in base_name
                                    for x in ("bist_endeks_bilesenleri", "hisse_endeks_ds")
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
        universe = parse_xutum(raw, f"acceptance:{sha[:12]}")
    except Exception:
        continue
    if not dates:
        continue
    snapshots.append(
        {
            "sha": sha,
            "date": max(dates),
            "symbols": tuple(universe.semboller),
            "symbol_set": frozenset(universe.semboller),
            "sources": tuple(rec["sources"]),
        }
    )

baseline = next((x for x in snapshots if x["sha"] == BASELINE_SHA), None)
terminal_candidates = [x for x in snapshots if x["date"] == TERMINAL_DATE]
terminal = (
    sorted(
        terminal_candidates,
        key=lambda x: (len(x["sources"]), len(x["symbols"])),
        reverse=True,
    )[0]
    if terminal_candidates
    else None
)

if baseline is None:
    raise RuntimeError("ACCEPTANCE_BASELINE17_EXACT_MISSING")
if terminal is None:
    raise RuntimeError("ACCEPTANCE_TERMINAL25_MISSING")

expected_added = {symbol for _d, symbol in LEDGER}
actual_added = terminal["symbol_set"] - baseline["symbol_set"]
actual_removed = baseline["symbol_set"] - terminal["symbol_set"]

if actual_added != expected_added or actual_removed:
    raise RuntimeError(
        "ACCEPTANCE_UNIVERSE_RECONCILIATION_CHANGED:"
        f"added={sorted(actual_added)} removed={sorted(actual_removed)}"
    )

current = set(baseline["symbols"])
ledger_by_date = defaultdict(list)
for effective, symbol in LEDGER:
    ledger_by_date[effective].append(symbol)

universes: dict[date, tuple[str, ...]] = {}
for target in TARGET_DATES:
    for symbol in ledger_by_date.get(target, ()):
        current.add(symbol)
    universes[target] = tuple(sorted(current))

if frozenset(universes[TERMINAL_DATE]) != terminal["symbol_set"]:
    raise RuntimeError("ACCEPTANCE_RECONSTRUCTED_TERMINAL_MISMATCH")

print()
print("=== HISTORICAL UNIVERSE ACCEPTANCE ===")
print("BASELINE17_EXACT=PASS")
print("LEDGER_RECONCILIATION=PASS")
print(
    "UNIVERSE_COUNTS="
    + " | ".join(
        f"{d.isoformat()}:{len(universes[d])}" for d in TARGET_DATES
    )
)

existing_history = RankObservationJsonlStore().list()
profile = "dengeli"

if existing_history:
    latest_as_of = max(item.as_of for item in existing_history)
    latest_items = [item for item in existing_history if item.as_of == latest_as_of]
    nonblank = [item.profile_name for item in latest_items if item.profile_name.strip()]
    if nonblank:
        candidate = Counter(nonblank).most_common(1)[0][0]
        try:
            MarketScanRequest(
                evren="BIST Tüm",
                profil_adi=candidate,
                maksimum_aday=100,
                internetten_evren_guncelle=False,
            )
        except Exception:
            pass
        else:
            profile = candidate

print()
print("=== REPLAY CONTRACT ===")
print(f"PROFILE={profile}")
print(f"UNIVERSE_SOURCE={HISTORICAL_REPLAY_UNIVERSE_SOURCE}")
print("ROWS=FULL_FILTERED_RESEARCH")
print("PERSISTENCE=DISABLED")

all_observations = []
session_results = []

print()
print("=== 6-SESSION ADAPTER ACCEPTANCE ===")

for target in TARGET_DATES:
    result = replay_canonical_research(
        as_of=target,
        symbols=universes[target],
        profile_name=profile,
        universe_source=HISTORICAL_REPLAY_UNIVERSE_SOURCE,
    )

    if result.as_of != target.isoformat():
        raise RuntimeError(f"AS_OF_MISMATCH:{target}")
    if result.input_universe_size != len(universes[target]):
        raise RuntimeError(f"INPUT_UNIVERSE_SIZE_MISMATCH:{target}")
    if result.ranked_research_count != len(result.rows):
        raise RuntimeError(f"RANKED_ROW_COUNT_MISMATCH:{target}")
    if result.ranked_research_count != len(result.observations):
        raise RuntimeError(f"OBSERVATION_COUNT_MISMATCH:{target}")
    if result.ranked_research_count <= 0:
        raise RuntimeError(f"EMPTY_RESEARCH:{target}")

    ranks = [int(row["Sıra"]) for row in result.rows]
    if ranks != list(range(1, len(ranks) + 1)):
        raise RuntimeError(f"NONCONTIGUOUS_RANKS:{target}")

    symbols = [str(row["Hisse"]) for row in result.rows]
    if len(symbols) != len(set(symbols)):
        raise RuntimeError(f"DUPLICATE_RANK_SYMBOL:{target}")

    all_observations.extend(result.observations)
    session_results.append(result)

    print(
        f"SESSION={target.isoformat()} "
        f"universe={result.input_universe_size} "
        f"success={result.successful_scan_count} "
        f"failed={result.failed_scan_count} "
        f"ranked_full={result.ranked_research_count} "
        f"stale={result.stale_analysis_count} "
        f"future=0"
    )

print()
print("=== TRAJECTORY ACCEPTANCE ===")

trajectories = build_rank_trajectories(tuple(all_observations))
comparable = [x for x in trajectories if x.comparable]
with_5s = [x for x in comparable if x.rank_5s is not None]
band = [x for x in with_5s if 22 <= x.current_rank <= 80]

healthy = build_daily_early_trajectory_candidates(
    trajectories,
    primary_symbols=(),
    limit=5,
    rank_min=22,
    rank_max=80,
)

if not with_5s:
    raise RuntimeError("NO_5S_TRAJECTORIES_AFTER_ADAPTER_INTEGRATION")

print(f"IN_MEMORY_OBSERVATIONS={len(all_observations)}")
print(f"TRAJECTORIES={len(trajectories)}")
print(f"COMPARABLE={len(comparable)}")
print(f"WITH_5S={len(with_5s)}")
print(f"BAND_22_80_WITH_5S={len(band)}")
print(f"HEALTHY_EARLY_COUNT={len(healthy)}")

print()
print("=== TOP 15 5S PATHS IN BAND 22..80 ===")

sorted_band = sorted(
    band,
    key=lambda x: (
        x.gain_3s is None,
        -(x.gain_3s or -10**9),
        x.gain_5s is None,
        -(x.gain_5s or -10**9),
        x.gain_1s is None,
        -(x.gain_1s or -10**9),
        x.current_rank,
        x.symbol,
    ),
)

for item in sorted_band[:15]:
    print(
        f"{item.symbol} | "
        f"{item.rank_5s} -> {item.rank_3s} -> {item.rank_1s} -> {item.current_rank} | "
        f"1S:{item.gain_1s:+d} "
        f"3S:{item.gain_3s:+d} "
        f"5S:{item.gain_5s:+d} | "
        f"lifecycle={item.lifecycle}"
    )

print()
print("=== HEALTHY EARLY TOP ===")
if not healthy:
    print("HEALTHY_EARLY=NONE")
else:
    for row in daily_early_trajectory_rows(healthy, start_priority=6):
        print(
            f"{row['Öncelik']}. {row['Hisse']} | "
            f"Sıra yolu: {row['Sıra yolu']} | "
            f"1S: {row['1S Δ']} | "
            f"3S: {row['3S Δ']} | "
            f"5S: {row['5S Δ']} | "
            f"{row['Hareket']}"
        )

memory_after = file_sha(memory_path)

print()
print("=== PERSISTENCE GUARD ===")
print("RANKING_MEMORY_SHA_AFTER=" + memory_after)
print(f"RANKING_MEMORY_UNCHANGED={'YES' if memory_before == memory_after else 'NO'}")

if memory_before != memory_after:
    raise RuntimeError("RANKING_MEMORY_CHANGED_DURING_READ_ONLY_ACCEPTANCE")

print()
print("=== FINAL POST-INTEGRATION DECISION ===")
print("POST_INTEGRATION_6SESSION_ACCEPTANCE=PROVEN")
print(
    "NEXT=PREPARE_IDEMPOTENT_HISTORICAL_RANKING_MEMORY_BACKFILL_WITH_BACKUP_DRYRUN_AND_ROLLBACK"
)
print("POST_INTEGRATION_ACCEPTANCE_CHECK=PASS")
'@

    [System.IO.File]::WriteAllText(
        $tmp,
        $code,
        (New-Object System.Text.UTF8Encoding($false))
    )

    # Windows PowerShell 5.1 can turn native STDERR into a terminating
    # NativeCommandError when $ErrorActionPreference = "Stop", even if Python
    # is still running normally. yfinance writes benign per-symbol warnings
    # (e.g. newly listed/delisted-looking tickers) to STDERR, so capture native
    # streams through Start-Process and judge success only by process ExitCode.
    $stdoutFile = Join-Path $env:TEMP "hisse_daily10_postintegration_stdout_$stamp.txt"
    $stderrFile = Join-Path $env:TEMP "hisse_daily10_postintegration_stderr_$stamp.txt"

    try {
        $proc = Start-Process `
            -FilePath $Python `
            -ArgumentList @($tmp, $ProjectRoot) `
            -Wait `
            -PassThru `
            -NoNewWindow `
            -RedirectStandardOutput $stdoutFile `
            -RedirectStandardError $stderrFile

        $stdoutLines = @()
        $stderrLines = @()

        if (Test-Path -LiteralPath $stdoutFile) {
            $stdoutLines = @(Get-Content -LiteralPath $stdoutFile -Encoding UTF8)
        }
        if (Test-Path -LiteralPath $stderrFile) {
            $stderrLines = @(Get-Content -LiteralPath $stderrFile -Encoding UTF8)
        }

        $output = @()
        if ($stdoutLines.Count -gt 0) {
            $output += $stdoutLines
        }
        if ($stderrLines.Count -gt 0) {
            $output += ""
            $output += "=== NATIVE STDERR (NON-FATAL UNLESS EXITCODE != 0) ==="
            $output += $stderrLines
        }

        $exit = [int]$proc.ExitCode

        $output | ForEach-Object { Write-Host $_ }
        [System.IO.File]::WriteAllLines(
            $report,
            @(
                "=== HISSE ROBOTU — POST-INTEGRATION 6-SESSION ACCEPTANCE V1 FIX1 ===",
                "MODE=READ_ONLY",
                "PRODUCTION_MUTATION=NO",
                "RANKING_MEMORY_WRITE=DISABLED",
                ("PYTHON_EXITCODE=" + $exit),
                ""
            ) + @($output | ForEach-Object { [string]$_ })
        )

        if ($exit -ne 0) {
            Write-Host ""
            Write-Host "=== FAILURE ==="
            Write-Host ("PYTHON_EXITCODE=" + $exit)
            Write-Host "POST_INTEGRATION_6SESSION_ACCEPTANCE=FAIL"
            Write-Host "RANKING_MEMORY_WRITE=DISABLED"
            Write-Host "PRODUCTION_MUTATION=NO"
            Write-Host ("REPORT=" + $report)
            throw "POST_INTEGRATION_ACCEPTANCE_FAIL"
        }
    }
    finally {
        Remove-Item -LiteralPath $stdoutFile -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $stderrFile -Force -ErrorAction SilentlyContinue
    }

    Write-Host ""
    Write-Host "=== SUCCESS ==="
    Write-Host "POST_INTEGRATION_6SESSION_ACCEPTANCE=PROVEN"
    Write-Host "RANKING_MEMORY_UNCHANGED=YES"
    Write-Host "POST_INTEGRATION_ACCEPTANCE_CHECK=PASS"
    Write-Host "NEXT=PREPARE_IDEMPOTENT_HISTORICAL_RANKING_MEMORY_BACKFILL_WITH_BACKUP_DRYRUN_AND_ROLLBACK"
    Write-Host ("REPORT=" + $report)
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
