param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$MemoryFile = Join-Path $ProjectRoot "data\ranking_memory\rank_observations.jsonl"
$Discovery = Join-Path $ProjectRoot "_discovery"

foreach ($p in @($Python, $MemoryFile)) {
    if (-not (Test-Path -LiteralPath $p -PathType Leaf)) {
        throw "REQUIRED_FILE_MISSING=$p"
    }
}

New-Item -ItemType Directory -Force -Path $Discovery | Out-Null

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$report = Join-Path $Discovery ("Hisse-Robotu-Daily10-18To24-History-Inventory-Preflight-V1-" + $stamp + ".txt")
$tmpPy = Join-Path $env:TEMP ("hisse_daily10_18to24_inventory_" + [guid]::NewGuid().ToString("N") + ".py")
$stdoutFile = Join-Path $env:TEMP ("hisse_daily10_18to24_inventory_out_" + [guid]::NewGuid().ToString("N") + ".txt")
$stderrFile = Join-Path $env:TEMP ("hisse_daily10_18to24_inventory_err_" + [guid]::NewGuid().ToString("N") + ".txt")

$oldPythonPath = $env:PYTHONPATH
$oldPythonUtf8 = $env:PYTHONUTF8
$oldPythonIoEncoding = $env:PYTHONIOENCODING

try {
    Write-Host "=== HISSE ROBOTU — DAILY10 18-24 AUG HISTORY INVENTORY PREFLIGHT V1 ==="
    Write-Host "MODE=READ_ONLY"
    Write-Host "PRODUCTION_MUTATION=NO"
    Write-Host "RANKING_MEMORY_WRITE=NO"
    Write-Host "TARGET_SESSIONS=2026-08-18,19,20,21,24"
    Write-Host "ANCHOR_SESSION=2026-08-25_CANONICAL_EXACT"
    Write-Host ""

    $env:PYTHONPATH = if ([string]::IsNullOrWhiteSpace($oldPythonPath)) {
        $ProjectRoot
    } else {
        "$ProjectRoot;$oldPythonPath"
    }
    $env:PYTHONUTF8 = "1"
    $env:PYTHONIOENCODING = "utf-8"

    $code = @'
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import zipfile
from collections import defaultdict
from datetime import date
from pathlib import Path

root = Path(sys.argv[1])

from backend.app.analysis.bist_universe import bist_bilesen_csvsini_ayristir
from backend.app.analysis.historical_research_replay import replay_canonical_research
from backend.app.analysis.ranking_memory import RankObservationJsonlStore

BASELINE_SHA = "04017af0e22aefd23b02f75cc96fa71a4f80b5c1dc6ee661dd57f1052e4712ef"
BASELINE_DATE = date(2026, 8, 17)
ANCHOR_DATE = date(2026, 8, 25)
TARGET_DATES = (
    date(2026, 8, 18),
    date(2026, 8, 19),
    date(2026, 8, 20),
    date(2026, 8, 21),
    date(2026, 8, 24),
)
ALL_REPLAY_DATES = TARGET_DATES + (ANCHOR_DATE,)

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
raw_before = memory_path.read_bytes()
sha_before = hashlib.sha256(raw_before).hexdigest()
store = RankObservationJsonlStore()
existing = tuple(store.list())

if not existing:
    raise RuntimeError("PREFLIGHT_BLOCKED:NO_EXISTING_RANKING_MEMORY")

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

def try_parse_observation_date(raw: str) -> date | None:
    try:
        return parse_observation_date(raw)
    except ValueError:
        return None

def obs_payload(item):
    return (
        item.symbol,
        int(item.rank),
        int(item.ranked_universe_size),
        item.universe_source,
        item.profile_name,
    )

print("=== MEMORY STATUS ===")
print(f"OBSERVATIONS={len(existing)}")
print(f"SHA_BEFORE={sha_before}")
invalid = [x for x in existing if try_parse_observation_date(x.as_of) is None]
print(f"NON_DATE_ROWS={len(invalid)}")
print("NON_DATE_POLICY=PRESERVE_AND_IGNORE_FOR_SESSION_MATCHING")

# ------------------------------------------------------------------
# Recover the same exact 17-Aug universe authority used by V5.
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
        universe = parse_xutum(raw, f"history-preflight:{sha[:12]}")
    except Exception:
        continue
    if not dates:
        continue
    snapshots.append(
        {
            "sha": sha,
            "date": max(dates),
            "symbols": tuple(universe.semboller),
            "sources": tuple(rec["sources"]),
        }
    )

baseline = next((x for x in snapshots if x["sha"] == BASELINE_SHA), None)
if baseline is None:
    raise RuntimeError("PREFLIGHT_BLOCKED:BASELINE17_EXACT_MISSING")

discovery = root / "_discovery"
evidence_candidates = sorted(
    discovery.glob(
        "Hisse-Robotu-Daily10-PostIntegration-6Session-Acceptance-V1-FIX1-*.txt"
    ),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)

proven_evidence = None
for evidence_path in evidence_candidates:
    try:
        evidence_text = evidence_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        continue
    required = (
        "POST_INTEGRATION_6SESSION_ACCEPTANCE=PROVEN",
        "BASELINE17_EXACT=PASS",
        "LEDGER_RECONCILIATION=PASS",
        "RANKING_MEMORY_UNCHANGED=YES",
    )
    if all(marker in evidence_text for marker in required):
        proven_evidence = evidence_path
        break

if proven_evidence is None:
    raise RuntimeError("PREFLIGHT_BLOCKED:PROVEN_ACCEPTANCE_EVIDENCE_MISSING")

ledger_by_date: dict[date, list[str]] = defaultdict(list)
for effective, symbol in LEDGER:
    ledger_by_date[effective].append(symbol)

current = set(baseline["symbols"])
universes: dict[date, tuple[str, ...]] = {}
for target in ALL_REPLAY_DATES:
    for symbol in ledger_by_date.get(target, ()):
        current.add(symbol)
    universes[target] = tuple(sorted(current))

expected_added = {symbol for _d, symbol in LEDGER}
if (set(universes[ANCHOR_DATE]) - set(baseline["symbols"])) != expected_added:
    raise RuntimeError("PREFLIGHT_BLOCKED:LEDGER_RECONSTRUCTION_MISMATCH")

print()
print("=== UNIVERSE AUTHORITY ===")
print("BASELINE17_EXACT=PASS")
print("PREVIOUS_TERMINAL_UNIVERSE_ACCEPTANCE=PROVEN")
print(f"PROVEN_EVIDENCE={proven_evidence}")
print("LEDGER_RECONCILIATION=PASS")
print(
    "UNIVERSE_COUNTS="
    + " | ".join(
        f"{d.isoformat()}:{len(universes[d])}" for d in ALL_REPLAY_DATES
    )
)

# ------------------------------------------------------------------
# Prove the current 25-Aug operational source/profile contract by
# exact canonical parity. V5 success should make this exact now.
# ------------------------------------------------------------------
anchor_existing = [
    x for x in existing
    if try_parse_observation_date(x.as_of) == ANCHOR_DATE
]

groups: dict[tuple[str, str], list[object]] = defaultdict(list)
for item in anchor_existing:
    source = str(item.universe_source or "").strip()
    profile = str(item.profile_name or "").strip()
    if source and profile:
        groups[(source, profile)].append(item)

exact_contracts = []

print()
print("=== 25-AUG CANONICAL ANCHOR ===")
for (source, profile), items in sorted(
    groups.items(),
    key=lambda pair: (-len(pair[1]), pair[0][0], pair[0][1]),
):
    replay = replay_canonical_research(
        as_of=ANCHOR_DATE,
        symbols=universes[ANCHOR_DATE],
        profile_name=profile,
        universe_source=source,
    )
    generated = tuple(sorted(replay.observations, key=lambda x: x.rank))
    remembered = tuple(sorted(items, key=lambda x: x.rank))

    exact = (
        len(generated) == len(remembered)
        and all(
            obs_payload(a) == obs_payload(b)
            for a, b in zip(remembered, generated)
        )
    )

    print(
        f"SOURCE={source!r} PROFILE={profile!r} "
        f"remembered={len(remembered)} canonical={len(generated)} "
        f"EXACT={'YES' if exact else 'NO'}"
    )

    if exact:
        exact_contracts.append((source, profile, replay))

if len(exact_contracts) != 1:
    raise RuntimeError(
        "PREFLIGHT_BLOCKED:"
        f"EXACT_25AUG_OPERATIONAL_CONTRACT_COUNT={len(exact_contracts)}"
    )

selected_source, selected_profile, anchor_replay = exact_contracts[0]

print()
print("=== SELECTED OPERATIONAL CONTRACT ===")
print(f"UNIVERSE_SOURCE={selected_source}")
print(f"PROFILE_NAME={selected_profile}")
print(f"ANCHOR_CANONICAL_ROWS={len(anchor_replay.observations)}")
print("25AUG_CANONICAL_PARITY=EXACT")

# ------------------------------------------------------------------
# Inventory 18-24 existing history against canonical completed-date
# replay under the selected operational contract.
# ------------------------------------------------------------------
safe_states = {
    "ABSENT",
    "EXACT",
    "PARTIAL_PREFIX",
    "PARTIAL_SAME_DATE_SIGNATURE",
    "FULL_METADATA_REPAIR",
}

date_results = {}
global_cross_contract = []

print()
print("=== 18-24 HISTORY INVENTORY ===")

for target in TARGET_DATES:
    replay = replay_canonical_research(
        as_of=target,
        symbols=universes[target],
        profile_name=selected_profile,
        universe_source=selected_source,
    )
    generated = tuple(sorted(replay.observations, key=lambda x: x.rank))
    generated_symbols = {x.symbol for x in generated}

    same_contract = tuple(
        sorted(
            (
                x for x in existing
                if try_parse_observation_date(x.as_of) == target
                and x.universe_source == selected_source
                and x.profile_name == selected_profile
            ),
            key=lambda x: x.rank,
        )
    )

    cross_contract = [
        x for x in existing
        if try_parse_observation_date(x.as_of) == target
        and (
            x.universe_source != selected_source
            or x.profile_name != selected_profile
        )
        and x.symbol in generated_symbols
    ]

    if cross_contract:
        global_cross_contract.extend(cross_contract)

    if not generated:
        state = "MISMATCH_EMPTY_CANONICAL"
        details = "canonical=0"
    elif not same_contract:
        state = "ABSENT"
        details = f"old=0 canonical={len(generated)}"
    else:
        ranks = [int(x.rank) for x in same_contract]
        contiguous = ranks == list(range(1, len(same_contract) + 1))
        unique_symbols = len({x.symbol for x in same_contract}) == len(same_contract)
        unique_ranks = len(set(ranks)) == len(ranks)
        old_sizes = sorted({int(x.ranked_universe_size) for x in same_contract})
        generated_by_rank = {int(x.rank): x for x in generated}

        prefix_match = (
            contiguous
            and unique_symbols
            and unique_ranks
            and len(same_contract) <= len(generated)
            and all(
                generated_by_rank.get(int(old.rank)) is not None
                and generated_by_rank[int(old.rank)].symbol == old.symbol
                for old in same_contract
            )
        )

        exact = (
            len(same_contract) == len(generated)
            and all(
                obs_payload(a) == obs_payload(b)
                for a, b in zip(same_contract, generated)
            )
        )

        full_rank_metadata_repair = (
            len(same_contract) == len(generated)
            and prefix_match
            and not exact
        )

        old_partial_signature = (
            contiguous
            and unique_symbols
            and unique_ranks
            and len(same_contract) < len(generated)
            and old_sizes == [len(same_contract)]
        )

        overlap = len(
            {x.symbol for x in same_contract}
            & generated_symbols
        )

        if exact:
            state = "EXACT"
        elif full_rank_metadata_repair:
            state = "FULL_METADATA_REPAIR"
        elif prefix_match:
            state = "PARTIAL_PREFIX"
        elif old_partial_signature:
            state = "PARTIAL_SAME_DATE_SIGNATURE"
        else:
            state = "MISMATCH"

        details = (
            f"old={len(same_contract)} canonical={len(generated)} "
            f"old_sizes={old_sizes} contiguous={'YES' if contiguous else 'NO'} "
            f"prefix={'YES' if prefix_match else 'NO'} overlap={overlap}"
        )

    date_results[target] = {
        "state": state,
        "canonical": len(generated),
        "existing": len(same_contract),
        "cross_contract": len(cross_contract),
    }

    print(
        f"DATE={target.isoformat()} STATE={state} "
        f"CROSS_CONTRACT={len(cross_contract)} {details}"
    )

print()
print("=== PREFLIGHT DECISION ===")
unsafe_states = {
    target: info["state"]
    for target, info in date_results.items()
    if info["state"] not in safe_states
}

if global_cross_contract:
    for item in global_cross_contract[:10]:
        print(
            "CROSS_CONTRACT_CONFLICT="
            f"{item.as_of}|{item.symbol}|"
            f"{item.universe_source}|{item.profile_name}"
        )

if unsafe_states:
    for target, state in unsafe_states.items():
        print(f"UNSAFE_DATE={target.isoformat()} STATE={state}")

ready = not global_cross_contract and not unsafe_states

print(
    "NORMALIZATION_READINESS="
    + ("READY" if ready else "BLOCKED")
)
print(f"CROSS_CONTRACT_TOTAL={len(global_cross_contract)}")
print(f"UNSAFE_DATE_COUNT={len(unsafe_states)}")
print(
    "NEXT="
    + (
        "BUILD_ATOMIC_18_TO_24_NORMALIZER_WITH_BACKUP_EXACT_POST_PARITY_AND_REGRESSION"
        if ready
        else
        "DO_NOT_MUTATE;USE_PRINTED_DATE_CLASSIFICATION_AS_EXACT_FIX_INPUT"
    )
)

sha_after = hashlib.sha256(memory_path.read_bytes()).hexdigest()
print(f"SHA_AFTER={sha_after}")
if sha_after != sha_before:
    raise RuntimeError("READ_ONLY_GUARD_FAIL:RANKING_MEMORY_CHANGED")

print("RANKING_MEMORY_UNCHANGED=YES")
print("18TO24_HISTORY_INVENTORY_PREFLIGHT_V1=PASS")
'@

    [System.IO.File]::WriteAllText($tmpPy, $code, [System.Text.UTF8Encoding]::new($false))

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Python
    $psi.ArgumentList.Add($tmpPy)
    $psi.ArgumentList.Add($ProjectRoot)
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    $psi.StandardOutputEncoding = [System.Text.UTF8Encoding]::new($false)
    $psi.StandardErrorEncoding = [System.Text.UTF8Encoding]::new($false)

    $proc = New-Object System.Diagnostics.Process
    $proc.StartInfo = $psi
    [void]$proc.Start()

    $stdout = $proc.StandardOutput.ReadToEnd()
    $stderr = $proc.StandardError.ReadToEnd()
    $proc.WaitForExit()

    [System.IO.File]::WriteAllText($stdoutFile, $stdout, [System.Text.UTF8Encoding]::new($false))
    [System.IO.File]::WriteAllText($stderrFile, $stderr, [System.Text.UTF8Encoding]::new($false))

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
        $combined += "=== NATIVE STDERR ==="
        $combined += $stderrLines
    }

    $combined | ForEach-Object { Write-Host $_ }

    [System.IO.File]::WriteAllLines(
        $report,
        @(
            "=== HISSE ROBOTU — DAILY10 18-24 AUG HISTORY INVENTORY PREFLIGHT V1 ===",
            ("PYTHON_EXITCODE=" + [int]$proc.ExitCode),
            ""
        ) + @($combined | ForEach-Object { [string]$_ })
    )

    if ([int]$proc.ExitCode -ne 0) {
        Write-Host ""
        Write-Host "=== FAILURE ==="
        Write-Host "PRODUCTION_MUTATION=NO"
        Write-Host ("REPORT=" + $report)
        throw "18TO24_HISTORY_INVENTORY_PREFLIGHT_PYTHON_FAIL"
    }

    Write-Host ""
    Write-Host "=== COMPLETE ==="
    Write-Host "PRODUCTION_MUTATION=NO"
    Write-Host "RANKING_MEMORY_UNCHANGED=YES"
    Write-Host "18TO24_HISTORY_INVENTORY_PREFLIGHT_V1=COMPLETE"
    Write-Host ("REPORT=" + $report)
}
finally {
    foreach ($p in @($tmpPy, $stdoutFile, $stderrFile)) {
        if (Test-Path -LiteralPath $p) {
            Remove-Item -LiteralPath $p -Force -ErrorAction SilentlyContinue
        }
    }

    if ($null -eq $oldPythonPath) {
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    } else {
        $env:PYTHONPATH = $oldPythonPath
    }

    if ($null -eq $oldPythonUtf8) {
        Remove-Item Env:PYTHONUTF8 -ErrorAction SilentlyContinue
    } else {
        $env:PYTHONUTF8 = $oldPythonUtf8
    }

    if ($null -eq $oldPythonIoEncoding) {
        Remove-Item Env:PYTHONIOENCODING -ErrorAction SilentlyContinue
    } else {
        $env:PYTHONIOENCODING = $oldPythonIoEncoding
    }
}
