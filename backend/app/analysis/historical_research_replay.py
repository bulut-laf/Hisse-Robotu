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

from __future__ import annotations

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