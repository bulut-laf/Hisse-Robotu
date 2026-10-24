param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

$Required = @(
    (Join-Path $ProjectRoot "backend\app\analysis\bist_universe.py"),
    (Join-Path $ProjectRoot "backend\app\analysis\market_scanner.py"),
    (Join-Path $ProjectRoot "backend\app\analysis\stock_scanner.py"),
    (Join-Path $ProjectRoot "backend\app\data\batch_market_data.py"),
    (Join-Path $ProjectRoot "backend\app\analysis\ranking_memory.py"),
    (Join-Path $ProjectRoot "backend\app\analysis\ranking_trajectory.py"),
    (Join-Path $ProjectRoot "backend\app\analysis\daily_early_trajectory.py")
)

foreach ($p in @($Python) + $Required) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "REQUIRED_PATH_MISSING=$p"
    }
}

$oldPythonPath = $env:PYTHONPATH
$tmp = Join-Path $env:TEMP "hisse_daily10_canonical_cutdate_dryrun_v1.py"

try {
    Write-Host "=== HISSE ROBOTU — CANONICAL CUT-DATE REPLAY DRY-RUN V1 ==="
    Write-Host "MODE=READ_ONLY"
    Write-Host "PRODUCTION_MUTATION=NO"
    Write-Host "RANKING_MEMORY_WRITE=DISABLED"
    Write-Host "SIDE_EFFECT_PUBLISHERS=DISABLED_IN_MEMORY"
    Write-Host "TARGET_SESSIONS=2026-08-18,19,20,21,24,25"
    Write-Host "GOAL=CANONICAL_RESEARCH_RANKS_AND_5S_TRAJECTORY_PREVIEW"

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

from backend.app.analysis.bist_universe import (
    BistUniverse,
    bist_bilesen_csvsini_ayristir,
)
import backend.app.analysis.market_scanner as market_scanner
import backend.app.analysis.stock_scanner as stock_scanner
from backend.app.analysis.market_scanner import (
    BistMarketScannerService,
    MarketScanRequest,
)
from backend.app.analysis.stock_scanner import BatchStockScanner
from backend.app.analysis.ranking_memory import (
    RankObservationJsonlStore,
    observations_from_research_rows,
)
from backend.app.analysis.ranking_trajectory import build_rank_trajectories
from backend.app.analysis.daily_early_trajectory import (
    build_daily_early_trajectory_candidates,
    daily_early_trajectory_rows,
)

BASELINE_SHA = "04017af0e22aefd23b02f75cc96fa71a4f80b5c1dc6ee661dd57f1052e4712ef"
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

def sha256(raw: bytes) -> str:
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

def parse_xutum(raw: bytes, source: str) -> BistUniverse:
    return bist_bilesen_csvsini_ayristir(
        raw,
        evren_adi="BIST Tüm",
        endeks_kodu="XUTUM",
        kaynak=source,
        resmi_kaynaktan_guncel=False,
    )

def normalized_symbol(value: object) -> str:
    s = str(value or "").strip().upper()
    if not s:
        return ""
    if s.endswith(".E"):
        s = s[:-2]
    if "." not in s:
        s += ".IS"
    return s

# ------------------------------------------------------------------
# 1) Recover exact 17 Aug anchor + best 25 Aug anchor from local bytes.
# ------------------------------------------------------------------
records: dict[str, dict[str, object]] = {}

def add_raw(raw: bytes, source: str) -> None:
    sha = sha256(raw)
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

# Git history in the project.
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
            "date": max(dates),
            "symbols": tuple(universe.semboller),
            "symbol_set": frozenset(universe.semboller),
            "count": len(universe.semboller),
            "sources": tuple(rec["sources"]),
        }
    )

baseline = next((x for x in snapshots if x["sha"] == BASELINE_SHA), None)
terminal_candidates = [x for x in snapshots if x["date"] == TERMINAL_DATE]
terminal = (
    sorted(
        terminal_candidates,
        key=lambda x: (len(x["sources"]), x["count"]),
        reverse=True,
    )[0]
    if terminal_candidates
    else None
)

print()
print("=== UNIVERSE ANCHORS ===")
print(f"BASELINE_EXACT={'YES' if baseline else 'NO'}")
print(f"TERMINAL_25={'YES' if terminal else 'NO'}")
if not baseline or not terminal:
    raise RuntimeError("UNIVERSE_ANCHOR_MISSING")

actual_added = terminal["symbol_set"] - baseline["symbol_set"]
actual_removed = baseline["symbol_set"] - terminal["symbol_set"]
expected_added = {symbol for _d, symbol in LEDGER}

print("ACTUAL_ADDED=" + (",".join(sorted(actual_added)) or "NONE"))
print("ACTUAL_REMOVED=" + (",".join(sorted(actual_removed)) or "NONE"))
print("EXPECTED_ADDED=" + ",".join(sorted(expected_added)))

if actual_added != expected_added or actual_removed:
    raise RuntimeError("UNIVERSE_LEDGER_NO_LONGER_RECONCILES")

baseline_sorted = tuple(sorted(baseline["symbols"]))
terminal_sorted = tuple(sorted(terminal["symbols"]))
order_contract_ok = (
    baseline_sorted == tuple(baseline["symbols"])
    and terminal_sorted == tuple(terminal["symbols"])
)
print(f"CANONICAL_SYMBOL_ORDER_ALPHABETIC={'YES' if order_contract_ok else 'NO'}")
if not order_contract_ok:
    raise RuntimeError("UNIVERSE_ORDER_CONTRACT_NOT_PROVEN")

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
    raise RuntimeError("RECONSTRUCTED_TERMINAL_MISMATCH")

print(
    "UNIVERSE_COUNTS="
    + " | ".join(
        f"{d.isoformat()}:{len(universes[d])}" for d in TARGET_DATES
    )
)

# ------------------------------------------------------------------
# 2) Prove the price seam accepts an explicit historical upper date.
# ------------------------------------------------------------------
from backend.app.data.batch_market_data import toplu_fiyat_verisi_getir as canonical_fetch

fetch_sig = inspect.signature(canonical_fetch)
print()
print("=== CUT-DATE PRICE SEAM ===")
print(f"FETCH_SIGNATURE={fetch_sig}")
if "bugun" not in fetch_sig.parameters:
    raise RuntimeError("CUTDATE_PRICE_SEAM_MISSING_BUGUN")
print("CUTDATE_PRICE_SEAM=PROVEN")

# ------------------------------------------------------------------
# 3) Disable all known project writes/publishers in memory.
# ------------------------------------------------------------------
side_effect_names = (
    "persist_research_rank_snapshot",
    "write_scan_row_opinion",
)
disabled = []
for name in side_effect_names:
    if hasattr(market_scanner, name):
        setattr(market_scanner, name, lambda *a, **k: 0)
        disabled.append(f"market_scanner.{name}")

print()
print("=== SIDE EFFECT GUARD ===")
print("DISABLED=" + (",".join(disabled) or "NONE_PRESENT"))
print("RANKING_MEMORY_APPEND=NOT_CALLED")

# ------------------------------------------------------------------
# 4) Resolve the production Research profile from latest memory if possible.
# ------------------------------------------------------------------
existing_history = RankObservationJsonlStore().list()
profile = "dengeli"

if existing_history:
    latest_as_of = max(item.as_of for item in existing_history)
    latest_items = [item for item in existing_history if item.as_of == latest_as_of]
    nonblank = [item.profile_name for item in latest_items if item.profile_name.strip()]
    if nonblank:
        candidate = Counter(nonblank).most_common(1)[0][0]
        try:
            # MarketScanRequest validates the profile through profil_al.
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
print("=== RESEARCH CONTRACT ===")
print(f"PROFILE={profile}")
print("UNIVERSE_SOURCE=HISTORICAL_XUTUM_OFFICIAL_LEDGER_V1")
print("RANK_ROWS=FULL_FILTERED_RESEARCH_ORDER_NOT_DISPLAY_SLICE")

# ------------------------------------------------------------------
# 5) In-memory adapters.
# ------------------------------------------------------------------
class StaticHistoricalUniverseRepository:
    def __init__(self, target: date, symbols: tuple[str, ...]):
        self.target = target
        self.symbols = symbols

    def evreni_yukle(self, evren_adi: str, internetten_guncelle: bool = True):
        if evren_adi != "BIST Tüm":
            raise ValueError(f"Historical adapter only supports BIST Tüm, got {evren_adi}")
        return BistUniverse(
            ad="BIST Tüm",
            endeks_kodu="XUTUM",
            semboller=self.symbols,
            tarih=self.target.isoformat(),
            kaynak="HISTORICAL_XUTUM_OFFICIAL_LEDGER_V1",
            resmi_kaynaktan_guncel=False,
        )

original_stock_fetch = getattr(stock_scanner, "toplu_fiyat_verisi_getir", None)
if original_stock_fetch is None:
    raise RuntimeError("STOCK_SCANNER_FETCH_SYMBOL_MISSING")

stock_fetch_sig = inspect.signature(original_stock_fetch)

def build_cut_fetch(target: date):
    def cut_fetch(*args, **kwargs):
        kwargs = dict(kwargs)
        kwargs["bugun"] = target
        if "resmi_veriyi_birlestir" in stock_fetch_sig.parameters:
            # Prevent a latest/current official daily row from leaking into an old cut date.
            kwargs["resmi_veriyi_birlestir"] = False
        return original_stock_fetch(*args, **kwargs)
    return cut_fetch

def build_batch_scanner(cut_fetch):
    sig = inspect.signature(BatchStockScanner)
    params = sig.parameters

    # Prefer explicit dependency injection when current production exposes it.
    for name in ("veri_getirici", "data_fetcher", "fiyat_verisi_getirici"):
        if name in params:
            return BatchStockScanner(**{name: cut_fetch}), f"CTOR:{name}"

    # Otherwise use the module-level imported function seam for this process only.
    stock_scanner.toplu_fiyat_verisi_getir = cut_fetch
    return BatchStockScanner(), "MODULE_MONKEYPATCH"

all_observations = []
session_summaries = []
future_leak_total = 0

print()
print("=== 6-SESSION CANONICAL REPLAY ===")

for target in TARGET_DATES:
    cut_fetch = build_cut_fetch(target)
    scanner, injection_mode = build_batch_scanner(cut_fetch)

    repo = StaticHistoricalUniverseRepository(target, universes[target])
    service = BistMarketScannerService(
        evren_repository=repo,
        tarayici=scanner,
        vbts_scan_filter=None,
    )

    req_kwargs = dict(
        evren="BIST Tüm",
        profil_adi=profile,
        maksimum_aday=100,
        internetten_evren_guncelle=False,
    )
    if "sektor_baglami_aktif" in inspect.signature(MarketScanRequest).parameters:
        req_kwargs["sektor_baglami_aktif"] = False

    request = MarketScanRequest(**req_kwargs)

    result = service.calistir(request)

    full_candidates = tuple(result.filtrelenmis.adaylar)
    displayed = tuple(result.adaylar)

    prefix = full_candidates[: len(displayed)]
    prefix_ok = tuple(x.sembol for x in prefix) == tuple(x.sembol for x in displayed)
    if not prefix_ok:
        raise RuntimeError(f"DISPLAY_PREFIX_MISMATCH:{target.isoformat()}")

    rows = tuple(
        {
            "Sıra": rank,
            "Hisse": candidate.sembol.removesuffix(".IS"),
            "Skor": candidate.sinyal.skor,
        }
        for rank, candidate in enumerate(full_candidates, start=1)
    )

    if not rows:
        raise RuntimeError(f"EMPTY_FILTERED_RESEARCH:{target.isoformat()}")

    ranks = [int(row["Sıra"]) for row in rows]
    if ranks != list(range(1, len(rows) + 1)):
        raise RuntimeError(f"NONCONTIGUOUS_RANKS:{target.isoformat()}")

    symbols = [str(row["Hisse"]) for row in rows]
    if len(symbols) != len(set(symbols)):
        raise RuntimeError(f"DUPLICATE_RESEARCH_SYMBOL:{target.isoformat()}")

    analysis_dates = []
    for candidate in full_candidates:
        try:
            d = date.fromisoformat(str(candidate.analiz_tarihi))
        except Exception:
            continue
        analysis_dates.append(d)

    future = [d for d in analysis_dates if d > target]
    future_leak_total += len(future)
    if future:
        raise RuntimeError(
            f"FUTURE_LEAK:{target.isoformat()}:{max(future).isoformat()}"
        )

    exact_date_count = sum(1 for d in analysis_dates if d == target)
    stale_date_count = sum(1 for d in analysis_dates if d < target)

    observations = observations_from_research_rows(
        rows=rows,
        as_of=target.isoformat(),
        universe_source="HISTORICAL_XUTUM_OFFICIAL_LEDGER_V1",
        profile_name=profile,
    )

    if len(observations) != len(rows):
        raise RuntimeError(
            f"OBSERVATION_COUNT_MISMATCH:{target.isoformat()}:{len(observations)}!={len(rows)}"
        )

    all_observations.extend(observations)

    successful_count = len(tuple(result.filtrelenmis.adaylar)) + len(
        tuple(result.filtrelenmis.elenenler)
    ) if hasattr(result.filtrelenmis, "elenenler") else None

    summary = {
        "date": target.isoformat(),
        "universe": len(universes[target]),
        "ranked": len(rows),
        "displayed": len(displayed),
        "exact_date": exact_date_count,
        "stale_date": stale_date_count,
        "mode": injection_mode,
    }
    session_summaries.append(summary)

    print(
        f"SESSION={target.isoformat()} "
        f"universe={len(universes[target])} "
        f"ranked_full={len(rows)} "
        f"displayed={len(displayed)} "
        f"analysis_on_cut={exact_date_count} "
        f"analysis_stale={stale_date_count} "
        f"future=0 "
        f"price_adapter={injection_mode}"
    )

# Restore process-local symbol after replay.
stock_scanner.toplu_fiyat_verisi_getir = original_stock_fetch

print()
print("=== TRAJECTORY BUILD ===")
trajectories = build_rank_trajectories(tuple(all_observations))
comparable = [x for x in trajectories if x.comparable]
with_5s = [
    x for x in comparable
    if x.rank_5s is not None
]
band = [
    x for x in with_5s
    if 22 <= x.current_rank <= 80
]

healthy = build_daily_early_trajectory_candidates(
    trajectories,
    primary_symbols=(),
    limit=5,
    rank_min=22,
    rank_max=80,
)

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

print()
print("=== FINAL DRY-RUN DECISION ===")
if future_leak_total != 0:
    print("CANONICAL_CUTDATE_DRYRUN=FAIL_FUTURE_LEAK")
elif len(all_observations) == 0 or len(with_5s) == 0:
    print("CANONICAL_CUTDATE_DRYRUN=FAIL_NO_USABLE_5S")
else:
    print("CANONICAL_CUTDATE_DRYRUN=PROVEN")
    print(
        "NEXT=PACKAGE_MINIMAL_OPT_IN_REPLAY_ADAPTER_FOR_REPO;"
        "KEEP_RANKING_MEMORY_WRITE_DISABLED_UNTIL_POST_INTEGRATION_REGRESSION"
    )

print("CANONICAL_CUTDATE_REPLAY_DRYRUN=PASS")
'@

    [System.IO.File]::WriteAllText(
        $tmp,
        $code,
        (New-Object System.Text.UTF8Encoding($false))
    )

    & $Python $tmp $ProjectRoot
    if ($LASTEXITCODE -ne 0) {
        throw "CANONICAL_CUTDATE_REPLAY_DRYRUN_FAIL"
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
