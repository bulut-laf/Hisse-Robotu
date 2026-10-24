param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$MemoryFile = Join-Path $ProjectRoot "data\ranking_memory\rank_observations.jsonl"
$Discovery = Join-Path $ProjectRoot "_discovery"

$Required = @(
    $Python,
    (Join-Path $ProjectRoot "backend\app\analysis\historical_research_replay.py"),
    (Join-Path $ProjectRoot "backend\app\analysis\bist_universe.py"),
    (Join-Path $ProjectRoot "backend\app\analysis\ranking_memory.py"),
    (Join-Path $ProjectRoot "backend\app\analysis\ranking_trajectory.py"),
    (Join-Path $ProjectRoot "backend\app\analysis\daily_early_trajectory.py"),
    (Join-Path $ProjectRoot "backend\tests\test_historical_research_replay_v1.py"),
    (Join-Path $ProjectRoot "backend\tests\test_daily_early_trajectory_v1.py")
)

foreach ($p in $Required) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "REQUIRED_PATH_MISSING=$p"
    }
}

New-Item -ItemType Directory -Path $Discovery -Force | Out-Null

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$rollback = Join-Path $ProjectRoot "_rollback\daily10-ranking-memory-backfill-v1-$stamp"
$report = Join-Path $Discovery "Hisse-Robotu-Daily10-Ranking-Memory-Backfill-V1-$stamp.txt"

New-Item -ItemType Directory -Path $rollback -Force | Out-Null

$memoryExisted = Test-Path -LiteralPath $MemoryFile
$backupMemory = Join-Path $rollback "rank_observations.jsonl"

if ($memoryExisted) {
    Copy-Item -LiteralPath $MemoryFile -Destination $backupMemory -Force
}

function Restore-RankingMemory {
    if ($memoryExisted) {
        Copy-Item -LiteralPath $backupMemory -Destination $MemoryFile -Force
    }
    elseif (Test-Path -LiteralPath $MemoryFile) {
        Remove-Item -LiteralPath $MemoryFile -Force
    }
}

$oldPythonPath = $env:PYTHONPATH
$tmp = Join-Path $env:TEMP "hisse_daily10_ranking_memory_backfill_v1.py"
$stdoutFile = Join-Path $env:TEMP "hisse_daily10_backfill_stdout_$stamp.txt"
$stderrFile = Join-Path $env:TEMP "hisse_daily10_backfill_stderr_$stamp.txt"

try {
    Write-Host "=== HISSE ROBOTU — DAILY10 RANKING MEMORY BACKFILL V1 ==="
    Write-Host "MODE=CONTROLLED_DATA_MUTATION"
    Write-Host "SOURCE_CODE_MUTATION=NO"
    Write-Host "BACKUP=YES"
    Write-Host "DRYRUN_BEFORE_APPEND=YES"
    Write-Host "IDEMPOTENT_APPEND=YES"
    Write-Host "ROLLBACK_ON_ANY_FAILURE=YES"
    Write-Host "TARGET_SESSIONS=2026-08-18,19,20,21,24,25"

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
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import date
from pathlib import Path

root = Path(sys.argv[1])

from backend.app.analysis.bist_universe import bist_bilesen_csvsini_ayristir
from backend.app.analysis.historical_research_replay import replay_canonical_research
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

store = RankObservationJsonlStore()
existing = tuple(store.list())

if not existing:
    raise RuntimeError(
        "BACKFILL_CONTRACT_BLOCKED:NO_EXISTING_RANKING_MEMORY_FOR_25AUG_PARITY"
    )

def parse_observation_date(raw: str) -> date:
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
            continue
    raise ValueError(f"Unsupported ranking-memory date: {value!r}")

def obs_tuple(item):
    return (
        item.as_of,
        item.symbol,
        item.rank,
        item.ranked_universe_size,
        item.universe_source,
        item.profile_name,
    )

def key(item):
    return (
        item.as_of,
        item.symbol,
        item.universe_source,
        item.profile_name,
    )

def file_sha(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    return hashlib.sha256(path.read_bytes()).hexdigest()

memory_path = root / "data" / "ranking_memory" / "rank_observations.jsonl"
sha_before = file_sha(memory_path)

print()
print("=== EXISTING RANKING MEMORY ===")
print(f"OBSERVATIONS_BEFORE={len(existing)}")
print(f"SHA_BEFORE={sha_before}")

# ------------------------------------------------------------------
# Recover exact historical XUTUM anchors and reconstruct six universes.
# ------------------------------------------------------------------
records: dict[str, dict[str, object]] = {}

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
            marker = str(path.resolve())
        except OSError:
            marker = str(path)
        if marker in seen:
            continue
        seen.add(marker)

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
        universe = parse_xutum(raw, f"backfill:{sha[:12]}")
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
    raise RuntimeError("BACKFILL_BLOCKED:BASELINE17_EXACT_MISSING")
if terminal is None:
    raise RuntimeError("BACKFILL_BLOCKED:TERMINAL25_MISSING")

expected_added = {symbol for _d, symbol in LEDGER}
actual_added = terminal["symbol_set"] - baseline["symbol_set"]
actual_removed = baseline["symbol_set"] - terminal["symbol_set"]

if actual_added != expected_added or actual_removed:
    raise RuntimeError(
        "BACKFILL_BLOCKED:UNIVERSE_RECONCILIATION_CHANGED:"
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
    raise RuntimeError("BACKFILL_BLOCKED:RECONSTRUCTED_25_MISMATCH")

print()
print("=== UNIVERSE CONTRACT ===")
print("BASELINE17_EXACT=PASS")
print("LEDGER_RECONCILIATION=PASS")
print(
    "UNIVERSE_COUNTS="
    + " | ".join(
        f"{d.isoformat()}:{len(universes[d])}" for d in TARGET_DATES
    )
)

# ------------------------------------------------------------------
# Find the one existing 25-Aug Research source/profile contract that
# exactly matches a fresh canonical historical replay.
# ------------------------------------------------------------------
anchor_existing = [
    item for item in existing
    if parse_observation_date(item.as_of) == TERMINAL_DATE
]

if not anchor_existing:
    raise RuntimeError(
        "BACKFILL_CONTRACT_BLOCKED:NO_EXISTING_25AUG_RANKING_MEMORY"
    )

groups: dict[tuple[str, str], list[object]] = defaultdict(list)
for item in anchor_existing:
    if item.universe_source.strip() and item.profile_name.strip():
        groups[(item.universe_source, item.profile_name)].append(item)

if not groups:
    raise RuntimeError(
        "BACKFILL_CONTRACT_BLOCKED:NO_NONBLANK_25AUG_SOURCE_PROFILE"
    )

profile_replays = {}
exact_contracts = []

print()
print("=== 25-AUG CONTRACT PARITY ===")
for (source, profile), items in sorted(
    groups.items(),
    key=lambda pair: (-len(pair[1]), pair[0][0], pair[0][1]),
):
    if profile not in profile_replays:
        profile_replays[profile] = replay_canonical_research(
            as_of=TERMINAL_DATE,
            symbols=universes[TERMINAL_DATE],
            profile_name=profile,
            universe_source=source,
        )

    base_result = profile_replays[profile]

    # Re-materialize observations with the exact candidate source when the
    # profile replay was cached under another source.
    if base_result.universe_source == source:
        candidate_result = base_result
    else:
        candidate_result = replay_canonical_research(
            as_of=TERMINAL_DATE,
            symbols=universes[TERMINAL_DATE],
            profile_name=profile,
            universe_source=source,
        )

    generated = {
        item.symbol: (item.rank, item.ranked_universe_size)
        for item in candidate_result.observations
    }
    remembered = {
        item.symbol: (item.rank, item.ranked_universe_size)
        for item in items
    }

    exact = generated == remembered
    print(
        f"SOURCE={source!r} PROFILE={profile!r} "
        f"remembered={len(remembered)} replay={len(generated)} "
        f"EXACT={'YES' if exact else 'NO'}"
    )

    if exact:
        exact_contracts.append((source, profile, candidate_result))

if len(exact_contracts) != 1:
    raise RuntimeError(
        "BACKFILL_CONTRACT_BLOCKED:"
        f"EXACT_25AUG_CONTRACT_MATCH_COUNT={len(exact_contracts)}"
    )

selected_source, selected_profile, replay_25 = exact_contracts[0]

print()
print("=== SELECTED OPERATIONAL RESEARCH CONTRACT ===")
print(f"UNIVERSE_SOURCE={selected_source}")
print(f"PROFILE_NAME={selected_profile}")
print("25AUG_PARITY=EXACT")
print(
    "RATIONALE=Historical rows are allowed into operational Ranking Memory "
    "only because the existing 25-Aug canonical snapshot is byte-independent "
    "but rank-for-rank identical under this source/profile contract."
)

# ------------------------------------------------------------------
# Replay six sessions under the proven operational contract.
# ------------------------------------------------------------------
replay_results = {}

print()
print("=== SIX-SESSION BACKFILL DRY-RUN ===")

for target in TARGET_DATES:
    if target == TERMINAL_DATE:
        result = replay_25
    else:
        result = replay_canonical_research(
            as_of=target,
            symbols=universes[target],
            profile_name=selected_profile,
            universe_source=selected_source,
        )

    replay_results[target] = result
    print(
        f"SESSION={target.isoformat()} "
        f"universe={result.input_universe_size} "
        f"success={result.successful_scan_count} "
        f"failed={result.failed_scan_count} "
        f"ranked_full={result.ranked_research_count} "
        f"stale={result.stale_analysis_count} future=0"
    )

incoming = tuple(
    obs
    for target in TARGET_DATES
    for obs in replay_results[target].observations
)

# Existing same-session observations from another contract would make
# ranking_trajectory._session_map count the same date more than once.
target_date_set = set(TARGET_DATES)
incoming_symbols = {item.symbol for item in incoming}

cross_contract_same_session = []
for item in existing:
    try:
        item_date = parse_observation_date(item.as_of)
    except ValueError:
        continue
    if item_date not in target_date_set:
        continue
    if item.symbol not in incoming_symbols:
        continue
    if (
        item.universe_source != selected_source
        or item.profile_name != selected_profile
    ):
        cross_contract_same_session.append(item)

if cross_contract_same_session:
    examples = cross_contract_same_session[:10]
    for item in examples:
        print(
            "CROSS_CONTRACT_CONFLICT="
            f"{item.as_of}|{item.symbol}|{item.universe_source}|{item.profile_name}"
        )
    raise RuntimeError(
        "BACKFILL_CONTRACT_BLOCKED:"
        f"CROSS_CONTRACT_SAME_SESSION_COUNT={len(cross_contract_same_session)}"
    )

existing_by_key = {key(item): item for item in existing}
conflicts = []
planned_new = []
already_exact = []

for item in incoming:
    old = existing_by_key.get(key(item))
    if old is None:
        planned_new.append(item)
    elif obs_tuple(old) == obs_tuple(item):
        already_exact.append(item)
    else:
        conflicts.append((old, item))

if conflicts:
    for old, new in conflicts[:10]:
        print(
            "KEY_CONFLICT="
            f"old={obs_tuple(old)!r} new={obs_tuple(new)!r}"
        )
    raise RuntimeError(
        f"BACKFILL_BLOCKED:EXISTING_KEY_CONFLICT_COUNT={len(conflicts)}"
    )

planned_by_date = Counter(parse_observation_date(item.as_of) for item in planned_new)
exact_by_date = Counter(parse_observation_date(item.as_of) for item in already_exact)

print()
print("=== DRY-RUN APPEND PLAN ===")
print(f"INCOMING_TOTAL={len(incoming)}")
print(f"ALREADY_EXACT={len(already_exact)}")
print(f"PLANNED_NEW={len(planned_new)}")
print("CONFLICTS=0")
print("CROSS_CONTRACT_SAME_SESSION=0")

for target in TARGET_DATES:
    print(
        f"DATE={target.isoformat()} "
        f"already_exact={exact_by_date[target]} "
        f"planned_new={planned_by_date[target]}"
    )

# ------------------------------------------------------------------
# Controlled append. Store API is append-only and idempotent by key.
# ------------------------------------------------------------------
print()
print("=== CONTROLLED APPEND ===")

actual_added_total = 0
for target in TARGET_DATES:
    added = store.append_snapshot(replay_results[target].observations)
    actual_added_total += added
    print(f"DATE={target.isoformat()} ADDED={added}")

if actual_added_total != len(planned_new):
    raise RuntimeError(
        "BACKFILL_POSTWRITE_FAIL:"
        f"ADDED={actual_added_total} PLANNED={len(planned_new)}"
    )

after = tuple(store.list())
after_by_key = {key(item): item for item in after}

missing_after = []
mismatch_after = []

for item in incoming:
    saved = after_by_key.get(key(item))
    if saved is None:
        missing_after.append(item)
    elif obs_tuple(saved) != obs_tuple(item):
        mismatch_after.append((saved, item))

if missing_after or mismatch_after:
    raise RuntimeError(
        "BACKFILL_POSTWRITE_FAIL:"
        f"MISSING={len(missing_after)} MISMATCH={len(mismatch_after)}"
    )

sha_after = file_sha(memory_path)

print(f"OBSERVATIONS_AFTER={len(after)}")
print(f"ACTUAL_ADDED_TOTAL={actual_added_total}")
print(f"SHA_AFTER={sha_after}")

if actual_added_total > 0 and sha_after == sha_before:
    raise RuntimeError("BACKFILL_POSTWRITE_FAIL:SHA_DID_NOT_CHANGE")
if actual_added_total == 0 and sha_after != sha_before:
    raise RuntimeError("BACKFILL_POSTWRITE_FAIL:IDEMPOTENT_RERUN_CHANGED_FILE")

# ------------------------------------------------------------------
# Post-write trajectory validation: first the selected contract, then
# the exact all-memory path used by Daily10 runtime.
# ------------------------------------------------------------------
selected_history = tuple(
    item for item in after
    if item.universe_source == selected_source
    and item.profile_name == selected_profile
)

contract_trajectories = build_rank_trajectories(selected_history)
runtime_trajectories = build_rank_trajectories(after)

contract_map = {item.symbol: item for item in contract_trajectories}
runtime_map = {item.symbol: item for item in runtime_trajectories}

contract_with_5s = [
    item for item in contract_trajectories
    if item.rank_5s is not None
    and parse_observation_date(item.as_of) == TERMINAL_DATE
]

if not contract_with_5s:
    raise RuntimeError("BACKFILL_POSTWRITE_FAIL:NO_CONTRACT_5S_TRAJECTORIES")

runtime_mismatches = []

for contract_item in contract_with_5s:
    runtime_item = runtime_map.get(contract_item.symbol)
    if runtime_item is None:
        runtime_mismatches.append((contract_item.symbol, "MISSING"))
        continue

    contract_fields = (
        contract_item.current_rank,
        contract_item.rank_1s,
        contract_item.rank_3s,
        contract_item.rank_5s,
        contract_item.gain_1s,
        contract_item.gain_3s,
        contract_item.gain_5s,
    )
    runtime_fields = (
        runtime_item.current_rank,
        runtime_item.rank_1s,
        runtime_item.rank_3s,
        runtime_item.rank_5s,
        runtime_item.gain_1s,
        runtime_item.gain_3s,
        runtime_item.gain_5s,
    )

    if contract_fields != runtime_fields:
        runtime_mismatches.append(
            (contract_item.symbol, contract_fields, runtime_fields)
        )

if runtime_mismatches:
    for row in runtime_mismatches[:10]:
        print(f"RUNTIME_PATH_MISMATCH={row!r}")
    raise RuntimeError(
        "BACKFILL_POSTWRITE_FAIL:"
        f"DAILY10_RUNTIME_PATH_MISMATCH_COUNT={len(runtime_mismatches)}"
    )

healthy = build_daily_early_trajectory_candidates(
    runtime_trajectories,
    primary_symbols=(),
    limit=5,
    rank_min=22,
    rank_max=80,
)

print()
print("=== POST-WRITE TRAJECTORY VALIDATION ===")
print(f"SELECTED_CONTRACT_HISTORY={len(selected_history)}")
print(f"CONTRACT_5S_AT_25={len(contract_with_5s)}")
print("DAILY10_RUNTIME_PATH_PARITY=YES")
print(f"HEALTHY_EARLY_COUNT={len(healthy)}")

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

print()
print("BACKFILL_PYTHON_STAGE=PASS")
print(f"BACKFILL_NEW_OBSERVATIONS={actual_added_total}")
print("IDEMPOTENCY_GUARD=PASS")
print("POSTWRITE_TRAJECTORY_GUARD=PASS")
'@

    [System.IO.File]::WriteAllText(
        $tmp,
        $code,
        (New-Object System.Text.UTF8Encoding($false))
    )

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

    $combined = @()
    if ($stdoutLines.Count -gt 0) {
        $combined += $stdoutLines
    }
    if ($stderrLines.Count -gt 0) {
        $combined += ""
        $combined += "=== NATIVE STDERR (NON-FATAL UNLESS EXITCODE != 0) ==="
        $combined += $stderrLines
    }

    $combined | ForEach-Object { Write-Host $_ }

    if ([int]$proc.ExitCode -ne 0) {
        Restore-RankingMemory

        [System.IO.File]::WriteAllLines(
            $report,
            @(
                "=== HISSE ROBOTU — DAILY10 RANKING MEMORY BACKFILL V1 ===",
                "RESULT=PYTHON_STAGE_FAIL",
                "ROLLBACK=SUCCESS",
                "PRODUCTION_STATUS=PRE_BACKFILL_RESTORED",
                ("PYTHON_EXITCODE=" + [int]$proc.ExitCode),
                ""
            ) + @($combined | ForEach-Object { [string]$_ })
        )

        Write-Host ""
        Write-Host "=== FAILURE ==="
        Write-Host ("PYTHON_EXITCODE=" + [int]$proc.ExitCode)
        Write-Host "ROLLBACK=SUCCESS"
        Write-Host "PRODUCTION_STATUS=PRE_BACKFILL_RESTORED"
        Write-Host ("REPORT=" + $report)
        throw "RANKING_MEMORY_BACKFILL_PYTHON_STAGE_FAIL"
    }

    Write-Host ""
    Write-Host "=== TARGET TESTS ==="

    $targetOutput = & $Python -m pytest -q `
        backend/tests/test_historical_research_replay_v1.py `
        backend/tests/test_daily_early_trajectory_v1.py 2>&1
    $targetExit = $LASTEXITCODE
    $targetOutput | ForEach-Object { Write-Host $_ }

    if ($targetExit -ne 0) {
        Restore-RankingMemory

        [System.IO.File]::WriteAllLines(
            $report,
            @(
                "=== HISSE ROBOTU — DAILY10 RANKING MEMORY BACKFILL V1 ===",
                "RESULT=TARGET_TEST_FAIL",
                "ROLLBACK=SUCCESS",
                "PRODUCTION_STATUS=PRE_BACKFILL_RESTORED",
                ""
            ) +
            @($combined | ForEach-Object { [string]$_ }) +
            @("") +
            @($targetOutput | ForEach-Object { [string]$_ })
        )

        Write-Host ""
        Write-Host "=== FAILURE ==="
        Write-Host "ERROR=TARGET_TEST_FAIL"
        Write-Host "ROLLBACK=SUCCESS"
        Write-Host "PRODUCTION_STATUS=PRE_BACKFILL_RESTORED"
        Write-Host ("REPORT=" + $report)
        throw "RANKING_MEMORY_BACKFILL_TARGET_TEST_FAIL"
    }

    Write-Host ""
    Write-Host "=== FULL REGRESSION ==="

    $regOutput = & $Python -m pytest -q 2>&1
    $regExit = $LASTEXITCODE
    $regOutput | ForEach-Object { Write-Host $_ }

    if ($regExit -ne 0) {
        Restore-RankingMemory

        [System.IO.File]::WriteAllLines(
            $report,
            @(
                "=== HISSE ROBOTU — DAILY10 RANKING MEMORY BACKFILL V1 ===",
                "RESULT=FULL_REGRESSION_FAIL",
                "ROLLBACK=SUCCESS",
                "PRODUCTION_STATUS=PRE_BACKFILL_RESTORED",
                ""
            ) +
            @($combined | ForEach-Object { [string]$_ }) +
            @("") +
            @($targetOutput | ForEach-Object { [string]$_ }) +
            @("") +
            @($regOutput | ForEach-Object { [string]$_ })
        )

        Write-Host ""
        Write-Host "=== FAILURE ==="
        Write-Host "ERROR=FULL_REGRESSION_FAIL"
        Write-Host "ROLLBACK=SUCCESS"
        Write-Host "PRODUCTION_STATUS=PRE_BACKFILL_RESTORED"
        Write-Host ("REPORT=" + $report)
        throw "RANKING_MEMORY_BACKFILL_FULL_REGRESSION_FAIL"
    }

    [System.IO.File]::WriteAllLines(
        $report,
        @(
            "=== HISSE ROBOTU — DAILY10 RANKING MEMORY BACKFILL V1 ===",
            "RESULT=SUCCESS",
            "TARGET_TEST=PASS",
            "FULL_REGRESSION=PASS",
            "ROLLBACK=NOT_NEEDED",
            ""
        ) +
        @($combined | ForEach-Object { [string]$_ }) +
        @("") +
        @($targetOutput | ForEach-Object { [string]$_ }) +
        @("") +
        @($regOutput | ForEach-Object { [string]$_ })
    )

    Write-Host ""
    Write-Host "=== SUCCESS ==="
    Write-Host "BACKFILL_DRYRUN=PASS"
    Write-Host "IDEMPOTENT_APPEND=PASS"
    Write-Host "POSTWRITE_TRAJECTORY_GUARD=PASS"
    Write-Host "TARGET_TEST=PASS"
    Write-Host "FULL_REGRESSION=PASS"
    Write-Host "DAILY10_HISTORICAL_RANKING_MEMORY_BACKFILL_V1=COMPLETE"
    Write-Host "NEXT=RUN_ACTUAL_DAILY10_RUNTIME_PREVIEW_AND_VERIFY_HEALTHY_EARLY_OUTPUT"
    Write-Host ("REPORT=" + $report)
}
finally {
    Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $stdoutFile -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $stderrFile -Force -ErrorAction SilentlyContinue

    if ($null -eq $oldPythonPath) {
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    } else {
        $env:PYTHONPATH = $oldPythonPath
    }
}
