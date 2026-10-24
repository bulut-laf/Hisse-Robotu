param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Module = Join-Path $ProjectRoot "backend\app\analysis\historical_research_replay.py"
$Test = Join-Path $ProjectRoot "backend\tests\test_historical_research_replay_v1.py"
$Discovery = Join-Path $ProjectRoot "_discovery"

$Required = @(
    $Python,
    (Join-Path $ProjectRoot "backend\app\analysis\stock_scanner.py"),
    (Join-Path $ProjectRoot "backend\app\analysis\market_scanner.py"),
    (Join-Path $ProjectRoot "backend\app\analysis\scan_filter.py"),
    (Join-Path $ProjectRoot "backend\app\analysis\scan_profiles.py"),
    (Join-Path $ProjectRoot "backend\app\data\batch_market_data.py"),
    (Join-Path $ProjectRoot "backend\app\analysis\ranking_memory.py")
)

foreach ($p in $Required) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "REQUIRED_PATH_MISSING=$p"
    }
}

New-Item -ItemType Directory -Path $Discovery -Force | Out-Null

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$report = Join-Path $Discovery "Hisse-Robotu-Daily10-Historical-Replay-Adapter-V1-$stamp.txt"
$rollback = Join-Path $ProjectRoot "_rollback\daily10-historical-replay-adapter-v1-$stamp"
New-Item -ItemType Directory -Path $rollback -Force | Out-Null

$moduleExisted = Test-Path -LiteralPath $Module
$testExisted = Test-Path -LiteralPath $Test

if ($moduleExisted) {
    Copy-Item -LiteralPath $Module -Destination (Join-Path $rollback "historical_research_replay.py") -Force
}
if ($testExisted) {
    Copy-Item -LiteralPath $Test -Destination (Join-Path $rollback "test_historical_research_replay_v1.py") -Force
}

function Restore-Rollback {
    if ($moduleExisted) {
        Copy-Item -LiteralPath (Join-Path $rollback "historical_research_replay.py") -Destination $Module -Force
    } elseif (Test-Path -LiteralPath $Module) {
        Remove-Item -LiteralPath $Module -Force
    }

    if ($testExisted) {
        Copy-Item -LiteralPath (Join-Path $rollback "test_historical_research_replay_v1.py") -Destination $Test -Force
    } elseif (Test-Path -LiteralPath $Test) {
        Remove-Item -LiteralPath $Test -Force
    }
}

$oldPythonPath = $env:PYTHONPATH

try {
    Write-Host "=== HISSE ROBOTU — HISTORICAL RESEARCH REPLAY ADAPTER V1 ==="
    Write-Host "MODE=CONTROLLED_MUTATION"
    Write-Host "RANKING_MEMORY_WRITE=DISABLED"
    Write-Host "DEFAULT_LIVE_BEHAVIOR=UNCHANGED"
    Write-Host "NEW_ENGINE=NO"
    Write-Host "NEW_STORE=NO"

    $env:PYTHONPATH = if ([string]::IsNullOrWhiteSpace($oldPythonPath)) {
        $ProjectRoot
    } else {
        "$ProjectRoot;$oldPythonPath"
    }

    $moduleCode = @'
from __future__ import annotations

"""Read-only historical replay adapter for the canonical Research pipeline.

Bu katman yeni teknik skor, işlem sinyali veya AL/SAT kararı üretmez.
Mevcut BatchStockScanner + ScanProfile + scan_filter sözleşmesini geçmiş
bir tamamlanmış seansa güvenli biçimde yeniden uygular.

V1 guarantees:
- explicit cut-date price boundary;
- explicit historical universe input;
- canonical Research filtering/ranking path is reused;
- full filtered Research rows are returned, never the UI display slice;
- future-dated analysis is fail-closed;
- Ranking Memory is never written here;
- no new score, signal, trade decision, store, or ranking engine.
"""

from dataclasses import dataclass
from datetime import date
import inspect
from typing import Callable, Iterable

from .market_scanner import sembolleri_normalize_et
from .ranking_memory import RankObservation, observations_from_research_rows
from .scan_filter import tarama_sonucunu_filtrele
from .scan_profiles import profil_al
from .stock_scanner import BatchStockScanner, StockScanResult
from ..data.batch_market_data import (
    BatchMarketDataResult,
    toplu_fiyat_verisi_getir,
)


HISTORICAL_REPLAY_UNIVERSE_SOURCE = "HISTORICAL_XUTUM_OFFICIAL_LEDGER_V1"

BatchDataFetcher = Callable[..., BatchMarketDataResult]


@dataclass(frozen=True)
class HistoricalResearchReplayResult:
    as_of: str
    universe_source: str
    profile_name: str
    input_universe_size: int
    successful_scan_count: int
    failed_scan_count: int
    ranked_research_count: int
    stale_analysis_count: int
    rows: tuple[dict[str, object], ...]
    observations: tuple[RankObservation, ...]
    scan_result: StockScanResult


def build_cut_date_fetcher(
    as_of: date,
    *,
    base_fetcher: BatchDataFetcher = toplu_fiyat_verisi_getir,
) -> BatchDataFetcher:
    """Bind the canonical batch-data seam to one historical completed date."""

    if not isinstance(as_of, date):
        raise TypeError("as_of must be datetime.date")

    signature = inspect.signature(base_fetcher)
    if "bugun" not in signature.parameters:
        raise ValueError(
            "Historical replay requires a batch data fetcher with explicit "
            "'bugun' upper-date support."
        )

    supports_official_merge_toggle = (
        "resmi_veriyi_birlestir" in signature.parameters
    )

    def fetch_at_cut_date(*args: object, **kwargs: object) -> BatchMarketDataResult:
        call_kwargs = dict(kwargs)
        call_kwargs["bugun"] = as_of

        # A current/latest official daily row must never leak into an old replay.
        if supports_official_merge_toggle:
            call_kwargs["resmi_veriyi_birlestir"] = False

        return base_fetcher(*args, **call_kwargs)

    return fetch_at_cut_date


def _analysis_date(value: object) -> date:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("Historical replay candidate has no analysis date.")
    try:
        return date.fromisoformat(raw[:10])
    except ValueError as exc:
        raise ValueError(
            f"Historical replay candidate has invalid analysis date: {raw}"
        ) from exc


def replay_canonical_research(
    *,
    as_of: date,
    symbols: Iterable[str],
    profile_name: str = "dengeli",
    universe_source: str = HISTORICAL_REPLAY_UNIVERSE_SOURCE,
    base_fetcher: BatchDataFetcher = toplu_fiyat_verisi_getir,
) -> HistoricalResearchReplayResult:
    """Replay one Research session without persistence or trading authority."""

    normalized_symbols = sembolleri_normalize_et(tuple(symbols))
    if not normalized_symbols:
        raise ValueError("Historical replay requires at least one universe symbol.")

    profile = profil_al(profile_name)
    source = str(universe_source or "").strip()
    if not source:
        raise ValueError("Historical replay requires a stable universe_source.")

    cut_fetcher = build_cut_date_fetcher(
        as_of,
        base_fetcher=base_fetcher,
    )

    scanner = BatchStockScanner(veri_getirici=cut_fetcher)
    scan = scanner.tara(normalized_symbols)

    filtered = tarama_sonucunu_filtrele(
        tarama=scan,
        kriterler=profile.kriterler,
    )

    # IMPORTANT: use the complete canonical filtered Research order, not
    # MarketScanResult.adaylar / maximum-display slice.
    candidates = tuple(filtered.adaylar)

    future_dates: list[date] = []
    stale_analysis_count = 0

    for candidate in candidates:
        candidate_date = _analysis_date(candidate.analiz_tarihi)
        if candidate_date > as_of:
            future_dates.append(candidate_date)
        elif candidate_date < as_of:
            stale_analysis_count += 1

    if future_dates:
        latest = max(future_dates)
        raise ValueError(
            "Historical replay future leakage detected: "
            f"cut={as_of.isoformat()} latest_analysis={latest.isoformat()}"
        )

    rows = tuple(
        {
            "Sıra": rank,
            "Hisse": candidate.sembol.removesuffix(".IS"),
            "Skor": candidate.sinyal.skor,
        }
        for rank, candidate in enumerate(candidates, start=1)
    )

    ranks = tuple(int(row["Sıra"]) for row in rows)
    if ranks != tuple(range(1, len(rows) + 1)):
        raise ValueError("Historical Research ranks are not contiguous.")

    row_symbols = tuple(str(row["Hisse"]) for row in rows)
    if len(row_symbols) != len(set(row_symbols)):
        raise ValueError("Historical Research rows contain duplicate symbols.")

    observations = observations_from_research_rows(
        rows=rows,
        as_of=as_of.isoformat(),
        universe_source=source,
        profile_name=profile_name,
    )

    if len(observations) != len(rows):
        raise ValueError(
            "Historical Research row/observation count mismatch: "
            f"{len(rows)} != {len(observations)}"
        )

    return HistoricalResearchReplayResult(
        as_of=as_of.isoformat(),
        universe_source=source,
        profile_name=profile_name,
        input_universe_size=len(normalized_symbols),
        successful_scan_count=len(scan.basarili_sonuclar),
        failed_scan_count=len(scan.hatalar),
        ranked_research_count=len(rows),
        stale_analysis_count=stale_analysis_count,
        rows=rows,
        observations=observations,
        scan_result=scan,
    )
'@

    $testCode = @'
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from types import SimpleNamespace

import pytest

import backend.app.analysis.historical_research_replay as replay
from backend.app.data.batch_market_data import BatchMarketDataResult


def test_cut_date_fetcher_forwards_upper_date_and_disables_latest_official_merge():
    calls = []

    def fetcher(
        symbols,
        *,
        islem_gunu=160,
        indirme_donemi="1y",
        bugun=None,
        resmi_veriyi_birlestir=None,
    ):
        calls.append(
            {
                "symbols": tuple(symbols),
                "bugun": bugun,
                "resmi_veriyi_birlestir": resmi_veriyi_birlestir,
            }
        )
        return BatchMarketDataResult(veriler={}, hatalar=())

    cut = date(2026, 8, 21)
    bound = replay.build_cut_date_fetcher(cut, base_fetcher=fetcher)
    bound(("AAA.IS",), islem_gunu=160, indirme_donemi="1y")

    assert calls == [
        {
            "symbols": ("AAA.IS",),
            "bugun": cut,
            "resmi_veriyi_birlestir": False,
        }
    ]


def test_cut_date_fetcher_fails_closed_without_explicit_date_seam():
    def unsafe_fetcher(symbols, *, islem_gunu=160, indirme_donemi="1y"):
        return BatchMarketDataResult(veriler={}, hatalar=())

    with pytest.raises(ValueError, match="bugun"):
        replay.build_cut_date_fetcher(
            date(2026, 8, 21),
            base_fetcher=unsafe_fetcher,
        )


def test_replay_uses_full_filtered_research_rows_and_never_persists(monkeypatch):
    cut = date(2026, 8, 21)
    fetch_calls = []

    def fetcher(
        symbols,
        *,
        islem_gunu=160,
        indirme_donemi="1y",
        bugun=None,
    ):
        fetch_calls.append((tuple(symbols), bugun))
        return BatchMarketDataResult(veriler={}, hatalar=())

    candidates = tuple(
        SimpleNamespace(
            sembol=f"S{i:03d}.IS",
            analiz_tarihi=cut.isoformat(),
            sinyal=SimpleNamespace(skor=float(200 - i)),
        )
        for i in range(1, 121)
    )

    fake_scan = SimpleNamespace(
        basarili_sonuclar=candidates,
        hatalar=(),
    )

    class FakeScanner:
        def __init__(self, *, veri_getirici):
            self._fetch = veri_getirici

        def tara(self, symbols):
            self._fetch(
                symbols,
                islem_gunu=160,
                indirme_donemi="1y",
            )
            return fake_scan

    monkeypatch.setattr(replay, "BatchStockScanner", FakeScanner)
    monkeypatch.setattr(
        replay,
        "profil_al",
        lambda _name: SimpleNamespace(kriterler=object()),
    )
    monkeypatch.setattr(
        replay,
        "tarama_sonucunu_filtrele",
        lambda *, tarama, kriterler: SimpleNamespace(adaylar=candidates),
    )

    result = replay.replay_canonical_research(
        as_of=cut,
        symbols=("AAA", "BBB"),
        profile_name="dengeli",
        universe_source="TEST_HISTORICAL_XUTUM",
        base_fetcher=fetcher,
    )

    assert fetch_calls == [(("AAA.IS", "BBB.IS"), cut)]
    assert result.ranked_research_count == 120
    assert len(result.rows) == 120
    assert result.rows[0]["Sıra"] == 1
    assert result.rows[-1]["Sıra"] == 120
    assert len(result.observations) == 120

    # Adapter does not receive or construct RankObservationJsonlStore;
    # persistence is intentionally outside this capability.
    assert "RankObservationJsonlStore" not in replay.__dict__


def test_replay_fails_closed_on_future_analysis_date(monkeypatch):
    cut = date(2026, 8, 21)

    def fetcher(
        symbols,
        *,
        islem_gunu=160,
        indirme_donemi="1y",
        bugun=None,
    ):
        return BatchMarketDataResult(veriler={}, hatalar=())

    future_candidate = SimpleNamespace(
        sembol="AAA.IS",
        analiz_tarihi="2026-08-24",
        sinyal=SimpleNamespace(skor=90.0),
    )

    fake_scan = SimpleNamespace(
        basarili_sonuclar=(future_candidate,),
        hatalar=(),
    )

    class FakeScanner:
        def __init__(self, *, veri_getirici):
            self._fetch = veri_getirici

        def tara(self, symbols):
            self._fetch(symbols, islem_gunu=160, indirme_donemi="1y")
            return fake_scan

    monkeypatch.setattr(replay, "BatchStockScanner", FakeScanner)
    monkeypatch.setattr(
        replay,
        "profil_al",
        lambda _name: SimpleNamespace(kriterler=object()),
    )
    monkeypatch.setattr(
        replay,
        "tarama_sonucunu_filtrele",
        lambda *, tarama, kriterler: SimpleNamespace(
            adaylar=(future_candidate,)
        ),
    )

    with pytest.raises(ValueError, match="future leakage"):
        replay.replay_canonical_research(
            as_of=cut,
            symbols=("AAA",),
            base_fetcher=fetcher,
        )


def test_contract_phrase_is_preserved():
    source = replay.__doc__ or ""
    assert "yeni teknik skor, işlem sinyali veya AL/SAT kararı üretmez" in source
'@

    [System.IO.File]::WriteAllText(
        $Module,
        $moduleCode,
        (New-Object System.Text.UTF8Encoding($false))
    )
    [System.IO.File]::WriteAllText(
        $Test,
        $testCode,
        (New-Object System.Text.UTF8Encoding($false))
    )

    $logLines = New-Object System.Collections.Generic.List[string]
    $logLines.Add("=== HISSE ROBOTU — HISTORICAL RESEARCH REPLAY ADAPTER V1 ===")
    $logLines.Add("MODULE=backend/app/analysis/historical_research_replay.py")
    $logLines.Add("TEST=backend/tests/test_historical_research_replay_v1.py")
    $logLines.Add("RANKING_MEMORY_WRITE=DISABLED")
    $logLines.Add("DEFAULT_LIVE_BEHAVIOR=UNCHANGED")
    $logLines.Add("NEW_ENGINE=NO")
    $logLines.Add("NEW_STORE=NO")
    $logLines.Add("")

    Write-Host ""
    Write-Host "=== TARGET TEST ==="
    $targetOutput = & $Python -m pytest -q backend/tests/test_historical_research_replay_v1.py 2>&1
    $targetExit = $LASTEXITCODE
    $targetOutput | ForEach-Object { Write-Host $_; $logLines.Add([string]$_) }

    if ($targetExit -ne 0) {
        $logLines.Add("TARGET_TEST=FAIL")
        [System.IO.File]::WriteAllLines($report, $logLines)
        Restore-Rollback
        Write-Host ""
        Write-Host "=== FAILURE ==="
        Write-Host "ERROR=TARGET_TEST_FAIL"
        Write-Host "ROLLBACK=SUCCESS"
        Write-Host "PRODUCTION_STATUS=UNCHANGED"
        throw "TARGET_TEST_FAIL"
    }

    $logLines.Add("TARGET_TEST=PASS")
    $logLines.Add("")

    Write-Host ""
    Write-Host "=== FULL REGRESSION ==="
    $regOutput = & $Python -m pytest -q 2>&1
    $regExit = $LASTEXITCODE
    $regOutput | ForEach-Object { Write-Host $_; $logLines.Add([string]$_) }

    if ($regExit -ne 0) {
        $logLines.Add("FULL_REGRESSION=FAIL")
        [System.IO.File]::WriteAllLines($report, $logLines)
        Restore-Rollback
        Write-Host ""
        Write-Host "=== FAILURE ==="
        Write-Host "ERROR=FULL_REGRESSION_FAIL"
        Write-Host "ROLLBACK=SUCCESS"
        Write-Host "PRODUCTION_STATUS=UNCHANGED"
        throw "FULL_REGRESSION_FAIL"
    }

    $logLines.Add("FULL_REGRESSION=PASS")
    $logLines.Add("RANKING_MEMORY_WRITE=STILL_DISABLED")
    $logLines.Add("NEXT=RUN_POST_INTEGRATION_6_SESSION_ACCEPTANCE")
    $logLines.Add("HISTORICAL_REPLAY_ADAPTER_V1=COMPLETE")
    [System.IO.File]::WriteAllLines($report, $logLines)

    Write-Host ""
    Write-Host "=== SUCCESS ==="
    Write-Host "TARGET_TEST=PASS"
    Write-Host "FULL_REGRESSION=PASS"
    Write-Host "HISTORICAL_REPLAY_ADAPTER_V1=COMPLETE"
    Write-Host "RANKING_MEMORY_WRITE=STILL_DISABLED"
    Write-Host "NEXT=RUN_POST_INTEGRATION_6_SESSION_ACCEPTANCE"
    Write-Host ("REPORT=" + $report)
}
catch {
    if ((Test-Path -LiteralPath $Module) -and (Test-Path -LiteralPath $Test)) {
        # If failure happened after mutation but before an explicit rollback path,
        # restore conservatively.
        if ($_.Exception.Message -notin @("TARGET_TEST_FAIL","FULL_REGRESSION_FAIL")) {
            Restore-Rollback
            Write-Host "ROLLBACK=SUCCESS"
            Write-Host "PRODUCTION_STATUS=UNCHANGED"
        }
    }
    throw
}
finally {
    if ($null -eq $oldPythonPath) {
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    } else {
        $env:PYTHONPATH = $oldPythonPath
    }
}
