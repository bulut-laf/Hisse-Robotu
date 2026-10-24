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
    $MemoryFile,
    (Join-Path $ProjectRoot "backend\app\analysis\bist_universe.py"),
    (Join-Path $ProjectRoot "backend\app\analysis\historical_research_replay.py"),
    (Join-Path $ProjectRoot "backend\app\analysis\ranking_memory.py"),
    (Join-Path $ProjectRoot "backend\app\analysis\ranking_trajectory.py"),
    (Join-Path $ProjectRoot "backend\app\analysis\daily_early_trajectory.py")
)

foreach ($p in $Required) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "REQUIRED_PATH_MISSING=$p"
    }
}

New-Item -ItemType Directory -Force -Path $Discovery | Out-Null

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$rollback = Join-Path $ProjectRoot "_rollback\daily10-25aug-canonical-session-rebuild-v1-$stamp"
$backupMemory = Join-Path $rollback "rank_observations.jsonl"
$report = Join-Path $Discovery "Hisse-Robotu-Daily10-25Aug-Canonical-Session-Rebuild-V1-$stamp.txt"
$tmp = Join-Path $env:TEMP "hisse_daily10_25aug_canonical_session_rebuild_v1.py"
$stdoutFile = Join-Path $env:TEMP "hisse_daily10_25aug_rebuild_stdout_$stamp.txt"
$stderrFile = Join-Path $env:TEMP "hisse_daily10_25aug_rebuild_stderr_$stamp.txt"

New-Item -ItemType Directory -Force -Path $rollback | Out-Null
Copy-Item -LiteralPath $MemoryFile -Destination $backupMemory -Force

function Restore-RankingMemory {
    Copy-Item -LiteralPath $backupMemory -Destination $MemoryFile -Force
}

$oldPythonPath = $env:PYTHONPATH

try {
    Write-Host "=== HISSE ROBOTU — 25 AUG CANONICAL RANKING MEMORY SESSION REBUILD V1 ==="
    Write-Host "MODE=CONTROLLED_DATA_NORMALIZATION"
    Write-Host "SOURCE_CODE_MUTATION=NO"
    Write-Host "BACKUP=YES"
    Write-Host "DRYRUN_BEFORE_WRITE=YES"
    Write-Host "ATOMIC_SWAP=YES"
    Write-Host "ROLLBACK_ON_ANY_FAILURE=YES"
    Write-Host "TARGET_DATE=2026-08-25"
    Write-Host "UNRELATED_ROWS_BYTE_PRESERVATION=REQUIRED"
    Write-Host "CONTRACT_SELECTION=EXACT_OR_PREFIX_PARITY"
    Write-Host ""

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
import json
import os
import re
import stat
import subprocess
import sys
import zipfile
from collections import defaultdict
from dataclasses import asdict
from datetime import date
from pathlib import Path

root = Path(sys.argv[1])

from backend.app.analysis.bist_universe import bist_bilesen_csvsini_ayristir
from backend.app.analysis.historical_research_replay import replay_canonical_research
from backend.app.analysis.ranking_memory import RankObservationJsonlStore

BASELINE_SHA = "04017af0e22aefd23b02f75cc96fa71a4f80b5c1dc6ee661dd57f1052e4712ef"
BASELINE_DATE = date(2026, 8, 17)
TERMINAL_DATE = date(2026, 8, 25)

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
store = RankObservationJsonlStore()
existing = tuple(store.list())

if not existing:
    raise RuntimeError("REBUILD_BLOCKED:NO_EXISTING_RANKING_MEMORY")

def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

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

def obs_payload(item):
    return (
        item.symbol,
        int(item.rank),
        int(item.ranked_universe_size),
        item.universe_source,
        item.profile_name,
    )

def obs_key(item):
    return (
        item.as_of,
        item.symbol,
        item.universe_source,
        item.profile_name,
    )

sha_before = file_sha(memory_path)
raw_before = memory_path.read_bytes()
raw_lines = raw_before.splitlines(keepends=True)

print("=== EXISTING MEMORY ===")
print(f"OBSERVATIONS_BEFORE={len(existing)}")
print(f"SHA_BEFORE={sha_before}")
print(f"BYTES_BEFORE={len(raw_before)}")

# ------------------------------------------------------------------
# Recover the exact 17-Aug XUTUM baseline and reconcile to 25-Aug.
# This is the same proven universe authority chain used by the
# six-session acceptance/backfill preflight.
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
        universe = parse_xutum(raw, f"rebuild25:{sha[:12]}")
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
    raise RuntimeError("REBUILD_BLOCKED:BASELINE17_EXACT_MISSING")
if terminal is None:
    raise RuntimeError("REBUILD_BLOCKED:TERMINAL25_MISSING")

expected_added = {symbol for _d, symbol in LEDGER}
actual_added = terminal["symbol_set"] - baseline["symbol_set"]
actual_removed = baseline["symbol_set"] - terminal["symbol_set"]

if actual_added != expected_added or actual_removed:
    raise RuntimeError(
        "REBUILD_BLOCKED:UNIVERSE_RECONCILIATION_CHANGED:"
        f"added={sorted(actual_added)} removed={sorted(actual_removed)}"
    )

current = set(baseline["symbols"])
for effective, symbol in LEDGER:
    if effective <= TERMINAL_DATE:
        current.add(symbol)

universe25 = tuple(sorted(current))

if frozenset(universe25) != terminal["symbol_set"]:
    raise RuntimeError("REBUILD_BLOCKED:RECONSTRUCTED_25_MISMATCH")

print()
print("=== UNIVERSE CONTRACT ===")
print("BASELINE17_EXACT=PASS")
print("LEDGER_RECONCILIATION=PASS")
print(f"UNIVERSE25_COUNT={len(universe25)}")

# ------------------------------------------------------------------
# Identify the operational source/profile contract by exact parity or
# by strict prefix parity against the old display-sliced snapshot.
# ------------------------------------------------------------------
anchor_existing = [
    item
    for item in existing
    if parse_observation_date(item.as_of) == TERMINAL_DATE
]

if not anchor_existing:
    raise RuntimeError("REBUILD_BLOCKED:NO_EXISTING_25AUG_MEMORY")

groups: dict[tuple[str, str], list[object]] = defaultdict(list)
for item in anchor_existing:
    if item.universe_source.strip() and item.profile_name.strip():
        groups[(item.universe_source, item.profile_name)].append(item)

if not groups:
    raise RuntimeError("REBUILD_BLOCKED:NO_NONBLANK_25AUG_CONTRACT")

candidates = []

print()
print("=== 25-AUG PREFIX/EXACT CONTRACT PARITY ===")

for (source, profile), items in sorted(
    groups.items(),
    key=lambda pair: (-len(pair[1]), pair[0][0], pair[0][1]),
):
    try:
        replay = replay_canonical_research(
            as_of=TERMINAL_DATE,
            symbols=universe25,
            profile_name=profile,
            universe_source=source,
        )
    except Exception as exc:
        print(
            f"SOURCE={source!r} PROFILE={profile!r} "
            f"REPLAY=FAIL TYPE={type(exc).__name__}"
        )
        continue

    generated = tuple(sorted(replay.observations, key=lambda x: x.rank))
    remembered = tuple(sorted(items, key=lambda x: x.rank))

    ranks = [int(x.rank) for x in remembered]
    contiguous = ranks == list(range(1, len(remembered) + 1))
    unique_symbols = len({x.symbol for x in remembered}) == len(remembered)
    unique_ranks = len(set(ranks)) == len(ranks)

    generated_by_rank = {int(x.rank): x for x in generated}
    prefix_match = (
        contiguous
        and unique_symbols
        and unique_ranks
        and len(remembered) <= len(generated)
        and all(
            generated_by_rank.get(int(old.rank)) is not None
            and generated_by_rank[int(old.rank)].symbol == old.symbol
            for old in remembered
        )
    )

    exact = (
        len(remembered) == len(generated)
        and all(
            obs_payload(old) == obs_payload(new)
            for old, new in zip(remembered, generated)
        )
    )

    full_rank_metadata_repair = (
        len(remembered) == len(generated)
        and prefix_match
        and not exact
    )

    old_sizes = sorted({int(x.ranked_universe_size) for x in remembered})

    mode = (
        "EXACT"
        if exact
        else "FULL_RANK_METADATA_REPAIR"
        if full_rank_metadata_repair
        else "PARTIAL_PREFIX"
        if prefix_match
        else "NO_MATCH"
    )

    print(
        f"SOURCE={source!r} PROFILE={profile!r} "
        f"remembered={len(remembered)} replay={len(generated)} "
        f"old_sizes={old_sizes} contiguous={'YES' if contiguous else 'NO'} "
        f"MODE={mode}"
    )

    if prefix_match:
        candidates.append(
            {
                "source": source,
                "profile": profile,
                "remembered": remembered,
                "replay": replay,
                "generated": generated,
                "mode": mode,
            }
        )

if len(candidates) != 1:
    raise RuntimeError(
        "REBUILD_CONTRACT_BLOCKED:"
        f"PREFIX_OR_EXACT_MATCH_COUNT={len(candidates)}"
    )

selected = candidates[0]
selected_source = selected["source"]
selected_profile = selected["profile"]
remembered = selected["remembered"]
replay_25 = selected["replay"]
generated = selected["generated"]
selection_mode = selected["mode"]

if replay_25.ranked_research_count != len(generated):
    raise RuntimeError("REBUILD_BLOCKED:REPLAY_OBSERVATION_COUNT_MISMATCH")
if replay_25.ranked_research_count <= 0:
    raise RuntimeError("REBUILD_BLOCKED:EMPTY_CANONICAL_RESEARCH")

generated_ranks = [int(x.rank) for x in generated]
if generated_ranks != list(range(1, len(generated) + 1)):
    raise RuntimeError("REBUILD_BLOCKED:CANONICAL_RANKS_NONCONTIGUOUS")

generated_sizes = {int(x.ranked_universe_size) for x in generated}
if generated_sizes != {len(generated)}:
    raise RuntimeError(
        "REBUILD_BLOCKED:CANONICAL_RANKED_UNIVERSE_SIZE_INCONSISTENT:"
        f"{sorted(generated_sizes)} expected={len(generated)}"
    )

print()
print("=== SELECTED OPERATIONAL CONTRACT ===")
print(f"UNIVERSE_SOURCE={selected_source}")
print(f"PROFILE_NAME={selected_profile}")
print(f"SELECTION_MODE={selection_mode}")
print(f"REMEMBERED_ROWS={len(remembered)}")
print(f"CANONICAL_FULL_ROWS={len(generated)}")
print("PREFIX_RANK_PARITY=YES")

# ------------------------------------------------------------------
# Do not create same-symbol/same-session duplicates under another
# contract. ranking_trajectory currently treats each observation as a
# session point and cannot safely absorb such duplicates.
# ------------------------------------------------------------------
generated_symbols = {x.symbol for x in generated}
cross_contract = [
    item
    for item in anchor_existing
    if (
        item.universe_source != selected_source
        or item.profile_name != selected_profile
    )
    and item.symbol in generated_symbols
]

if cross_contract:
    for item in cross_contract[:10]:
        print(
            "CROSS_CONTRACT_CONFLICT="
            f"{item.as_of}|{item.symbol}|{item.universe_source}|{item.profile_name}"
        )
    raise RuntimeError(
        "REBUILD_CONTRACT_BLOCKED:"
        f"CROSS_CONTRACT_SAME_SESSION_COUNT={len(cross_contract)}"
    )

print("CROSS_CONTRACT_SAME_SESSION=0")

# ------------------------------------------------------------------
# Parse raw JSONL so every unrelated line can be preserved byte-for-byte.
# ------------------------------------------------------------------
parsed_lines = []

for index, raw_line in enumerate(raw_lines):
    if not raw_line.strip():
        parsed_lines.append((index, raw_line, None))
        continue
    try:
        payload = json.loads(raw_line.decode("utf-8-sig"))
    except Exception as exc:
        raise RuntimeError(
            f"REBUILD_BLOCKED:RAW_JSON_PARSE_FAIL_LINE={index + 1}:"
            f"{type(exc).__name__}"
        )
    parsed_lines.append((index, raw_line, payload))

def payload_is_selected(payload) -> bool:
    if payload is None:
        return False
    try:
        item_date = parse_observation_date(payload.get("as_of", ""))
    except ValueError:
        return False
    return (
        item_date == TERMINAL_DATE
        and str(payload.get("universe_source", "")) == selected_source
        and str(payload.get("profile_name", "")) == selected_profile
    )

target_indices = [
    index
    for index, _raw_line, payload in parsed_lines
    if payload_is_selected(payload)
]

if not target_indices:
    raise RuntimeError("REBUILD_BLOCKED:RAW_SELECTED_25AUG_ROWS_NOT_FOUND")

if len(target_indices) != len(remembered):
    raise RuntimeError(
        "REBUILD_BLOCKED:RAW_STORE_COUNT_MISMATCH:"
        f"raw={len(target_indices)} store={len(remembered)}"
    )

# Existing selected keys must be unique.
selected_keys = [obs_key(x) for x in remembered]
if len(selected_keys) != len(set(selected_keys)):
    raise RuntimeError("REBUILD_BLOCKED:DUPLICATE_EXISTING_SELECTED_KEYS")

newline = b"\r\n" if b"\r\n" in raw_before else b"\n"
replacement_lines = [
    (
        json.dumps(
            asdict(item),
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
        + newline
    )
    for item in generated
]

unrelated_before = [
    raw_line
    for _index, raw_line, payload in parsed_lines
    if not payload_is_selected(payload)
]

first_target = min(target_indices)
target_index_set = set(target_indices)

planned_lines = []
inserted = False

for index, raw_line, payload in parsed_lines:
    if index in target_index_set:
        if not inserted:
            planned_lines.extend(replacement_lines)
            inserted = True
        continue
    planned_lines.append(raw_line)

if not inserted:
    raise RuntimeError("REBUILD_BLOCKED:INSERT_POINT_MISSING")

planned_raw = b"".join(planned_lines)

current_selected_map = {
    (x.symbol, int(x.rank), int(x.ranked_universe_size))
    for x in remembered
}
generated_selected_map = {
    (x.symbol, int(x.rank), int(x.ranked_universe_size))
    for x in generated
}

mutation_needed = current_selected_map != generated_selected_map

print()
print("=== DRY-RUN NORMALIZATION PLAN ===")
print(f"OLD_SELECTED_ROWS={len(remembered)}")
print(f"NEW_SELECTED_ROWS={len(generated)}")
print(f"UNRELATED_RAW_LINES={len(unrelated_before)}")
print(f"MUTATION_NEEDED={'YES' if mutation_needed else 'NO'}")
print("UNRELATED_ROWS_POLICY=BYTE_FOR_BYTE_PRESERVE")
print("WRITE_POLICY=ATOMIC_TEMP_FILE_SWAP")

if selection_mode == "EXACT" and mutation_needed:
    raise RuntimeError("REBUILD_BLOCKED:EXACT_SELECTION_BUT_MUTATION_DIFFERS")

# ------------------------------------------------------------------
# Controlled atomic replacement.
# ------------------------------------------------------------------
if mutation_needed:
    temp_path = memory_path.with_name(
        memory_path.name + f".rebuild-{os.getpid()}.tmp"
    )
    try:
        with temp_path.open("wb") as handle:
            handle.write(planned_raw)
            handle.flush()
            os.fsync(handle.fileno())

        try:
            mode = stat.S_IMODE(memory_path.stat().st_mode)
            os.chmod(temp_path, mode)
        except OSError:
            pass

        os.replace(temp_path, memory_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()
else:
    planned_raw = raw_before

# ------------------------------------------------------------------
# Post-write exact parity + unrelated byte preservation + key integrity.
# ------------------------------------------------------------------
raw_after = memory_path.read_bytes()
sha_after = file_sha(memory_path)
after = tuple(store.list())

after_selected = tuple(
    sorted(
        (
            item
            for item in after
            if parse_observation_date(item.as_of) == TERMINAL_DATE
            and item.universe_source == selected_source
            and item.profile_name == selected_profile
        ),
        key=lambda x: x.rank,
    )
)

if len(after_selected) != len(generated):
    raise RuntimeError(
        "REBUILD_POSTWRITE_FAIL:"
        f"SELECTED_COUNT={len(after_selected)} EXPECTED={len(generated)}"
    )

for saved, expected in zip(after_selected, generated):
    if obs_payload(saved) != obs_payload(expected):
        raise RuntimeError(
            "REBUILD_POSTWRITE_FAIL:EXACT_CANONICAL_PARITY_MISMATCH:"
            f"saved={obs_payload(saved)!r} expected={obs_payload(expected)!r}"
        )

after_raw_lines = raw_after.splitlines(keepends=True)
unrelated_after = []

for index, raw_line in enumerate(after_raw_lines):
    if not raw_line.strip():
        unrelated_after.append(raw_line)
        continue
    payload = json.loads(raw_line.decode("utf-8-sig"))
    if not payload_is_selected(payload):
        unrelated_after.append(raw_line)

if unrelated_before != unrelated_after:
    raise RuntimeError("REBUILD_POSTWRITE_FAIL:UNRELATED_ROWS_BYTE_CHANGED")

all_keys = [obs_key(x) for x in after]
if len(all_keys) != len(set(all_keys)):
    raise RuntimeError("REBUILD_POSTWRITE_FAIL:DUPLICATE_KEYS_AFTER")

if mutation_needed and sha_after == sha_before:
    raise RuntimeError("REBUILD_POSTWRITE_FAIL:SHA_DID_NOT_CHANGE")
if not mutation_needed and sha_after != sha_before:
    raise RuntimeError("REBUILD_POSTWRITE_FAIL:NOOP_CHANGED_FILE")

print()
print("=== POST-WRITE 25-AUG PARITY ===")
print("25AUG_CANONICAL_PARITY=EXACT")
print(f"SELECTED_ROWS_AFTER={len(after_selected)}")
print(f"RANKED_UNIVERSE_SIZE={len(generated)}")
print("UNRELATED_ROWS_BYTE_PRESERVED=YES")
print("DUPLICATE_KEYS_AFTER=0")
print(f"SHA_AFTER={sha_after}")
print(f"ATOMIC_SWAP={'YES' if mutation_needed else 'NOT_NEEDED_ALREADY_EXACT'}")

print()
print("REBUILD_PYTHON_STAGE=PASS")
print(f"REBUILD_MUTATED={'YES' if mutation_needed else 'NO'}")
print("RANKING_MEMORY_25AUG_CANONICAL=YES")
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

    if ($proc.ExitCode -ne 0 -or -not ($stdoutLines -contains "REBUILD_PYTHON_STAGE=PASS")) {
        Restore-RankingMemory

        [System.IO.File]::WriteAllLines(
            $report,
            @(
                "=== HISSE ROBOTU — 25 AUG CANONICAL RANKING MEMORY SESSION REBUILD V1 ===",
                "RESULT=PYTHON_STAGE_FAIL",
                "ROLLBACK=SUCCESS",
                "PRODUCTION_STATUS=PRE_REBUILD_RESTORED",
                ("PYTHON_EXITCODE=" + $proc.ExitCode),
                ""
            ) + @($combined | ForEach-Object { [string]$_ })
        )

        Write-Host ""
        Write-Host "=== FAILURE ==="
        Write-Host "ERROR=25AUG_REBUILD_PYTHON_STAGE_FAIL"
        Write-Host "ROLLBACK=SUCCESS"
        Write-Host "PRODUCTION_STATUS=PRE_REBUILD_RESTORED"
        Write-Host ("REPORT=" + $report)
        throw "25AUG_CANONICAL_REBUILD_PYTHON_STAGE_FAIL"
    }

    $shaBeforeTests = (Get-FileHash -LiteralPath $MemoryFile -Algorithm SHA256).Hash

    Write-Host ""
    Write-Host "=== TARGET TESTS ==="

    $targetTests = @(
        "backend/tests/test_ranking_memory.py",
        "backend/tests/test_ranking_memory_full_research_capture_v2.py",
        "backend/tests/test_historical_research_replay_v1.py",
        "backend/tests/test_daily_early_trajectory_v1.py"
    ) | Where-Object { Test-Path -LiteralPath (Join-Path $ProjectRoot $_) }

    Set-Location $ProjectRoot
    $targetOutput = & $Python -m pytest -q @targetTests 2>&1
    $targetExit = $LASTEXITCODE
    $targetOutput | ForEach-Object { Write-Host $_ }

    if ($targetExit -ne 0) {
        Restore-RankingMemory

        [System.IO.File]::WriteAllLines(
            $report,
            @(
                "RESULT=TARGET_TEST_FAIL",
                "ROLLBACK=SUCCESS",
                "PRODUCTION_STATUS=PRE_REBUILD_RESTORED",
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
        Write-Host "PRODUCTION_STATUS=PRE_REBUILD_RESTORED"
        Write-Host ("REPORT=" + $report)
        throw "25AUG_CANONICAL_REBUILD_TARGET_TEST_FAIL"
    }

    $shaAfterTarget = (Get-FileHash -LiteralPath $MemoryFile -Algorithm SHA256).Hash
    if ($shaAfterTarget -ne $shaBeforeTests) {
        Restore-RankingMemory
        throw "TEST_SIDE_EFFECT_GUARD_FAIL:RANKING_MEMORY_CHANGED_DURING_TARGET_TESTS"
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
                "RESULT=FULL_REGRESSION_FAIL",
                "ROLLBACK=SUCCESS",
                "PRODUCTION_STATUS=PRE_REBUILD_RESTORED",
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
        Write-Host "PRODUCTION_STATUS=PRE_REBUILD_RESTORED"
        Write-Host ("REPORT=" + $report)
        throw "25AUG_CANONICAL_REBUILD_FULL_REGRESSION_FAIL"
    }

    $shaAfterRegression = (Get-FileHash -LiteralPath $MemoryFile -Algorithm SHA256).Hash
    if ($shaAfterRegression -ne $shaBeforeTests) {
        Restore-RankingMemory
        throw "TEST_SIDE_EFFECT_GUARD_FAIL:RANKING_MEMORY_CHANGED_DURING_FULL_REGRESSION"
    }

    [System.IO.File]::WriteAllLines(
        $report,
        @(
            "=== HISSE ROBOTU — 25 AUG CANONICAL RANKING MEMORY SESSION REBUILD V1 ===",
            "RESULT=SUCCESS",
            "SOURCE_CODE_MUTATION=NO",
            "BACKUP=YES",
            "25AUG_CANONICAL_PARITY=EXACT",
            "UNRELATED_ROWS_BYTE_PRESERVED=YES",
            "TARGET_TEST=PASS",
            "FULL_REGRESSION=PASS",
            "RANKING_MEMORY_TEST_SIDE_EFFECT=NONE",
            "NEXT=INVENTORY_AND_NORMALIZE_18_TO_24_OPERATIONAL_CONTRACT_HISTORY",
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
    Write-Host "25AUG_CANONICAL_SESSION_REBUILD=COMPLETE"
    Write-Host "25AUG_CANONICAL_PARITY=EXACT"
    Write-Host "UNRELATED_ROWS_BYTE_PRESERVED=YES"
    Write-Host "RANKING_MEMORY_TEST_SIDE_EFFECT=NONE"
    Write-Host "TARGET_TEST=PASS"
    Write-Host "FULL_REGRESSION=PASS"
    Write-Host "NEXT=INVENTORY_AND_NORMALIZE_18_TO_24_OPERATIONAL_CONTRACT_HISTORY"
    Write-Host ("REPORT=" + $report)
}
catch {
    if ($_.Exception.Message -notmatch "25AUG_CANONICAL_REBUILD_PYTHON_STAGE_FAIL|25AUG_CANONICAL_REBUILD_TARGET_TEST_FAIL|25AUG_CANONICAL_REBUILD_FULL_REGRESSION_FAIL") {
        Restore-RankingMemory
        Write-Host "ROLLBACK=SUCCESS"
        Write-Host "PRODUCTION_STATUS=PRE_REBUILD_RESTORED"
    }
    throw
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
