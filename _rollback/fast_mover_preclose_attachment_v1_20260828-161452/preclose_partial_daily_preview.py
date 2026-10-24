from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, time
from typing import Callable, Iterable
from zoneinfo import ZoneInfo

import pandas as pd

from backend.app.analysis.market_scanner import (
    MarketScanRequest,
    MarketScanResult,
)
from backend.app.analysis.stock_scanner import BatchStockScanner
from backend.app.compliance.dashboard_market_scanner_source_factory import (
    build_dashboard_market_scanner,
)
from backend.app.data.batch_market_data import (
    BatchMarketDataFailure,
    BatchMarketDataResult,
    toplu_fiyat_verisi_getir,
)
from backend.app.data.delayed_data_pilot import DelayedDataSnapshot
from backend.app.operations.scheduled_intraday_batch import (
    ScheduledIntradayBatchResult,
    fetch_scheduled_intraday_batch,
)

ISTANBUL = ZoneInfo("Europe/Istanbul")
PRECLOSE_START = time(17, 20)
CANONICAL_CLOSE_START = time(18, 30)

# PRECLOSE_PARTIAL_DAILY_OVERLAY_V1
# Non-canonical read-only preview. No persistence authority.


class PreclosePartialDailyPreviewError(ValueError):
    """Pre-close partial daily preview cannot be built safely."""


@dataclass(frozen=True)
class PreclosePreviewResult:
    observed_at: datetime
    scan_result: MarketScanResult
    partial_symbol_count: int
    intraday_failure_count: int
    preview_only: bool = True
    canonical: bool = False
    ranking_write_allowed: bool = False
    profile_write_allowed: bool = False
    al_sat_decision_allowed: bool = False


def _local_now(value: datetime | None) -> datetime:
    current = value or datetime.now(ISTANBUL)
    if current.tzinfo is None:
        return current.replace(tzinfo=ISTANBUL)
    return current.astimezone(ISTANBUL)


def _preclose_guard(observed_at: datetime) -> None:
    clock = observed_at.timetz().replace(tzinfo=None)
    if clock < PRECLOSE_START:
        raise PreclosePartialDailyPreviewError(
            "17:20 öncesinde pre-close preview çalıştırılamaz."
        )
    if clock >= CANONICAL_CLOSE_START:
        raise PreclosePartialDailyPreviewError(
            "18:30 ve sonrasında partial preview yerine canonical close kullanılmalıdır."
        )


def _date_index(frame: pd.DataFrame) -> pd.Index:
    return pd.Index(pd.to_datetime(frame.index).date)


def overlay_partial_daily_bar(
    completed_daily: pd.DataFrame,
    snapshot: DelayedDataSnapshot,
    *,
    observed_at: datetime,
) -> pd.DataFrame:
    """Append/replace today's synthetic daily row using current intraday evidence."""

    if completed_daily is None or completed_daily.empty:
        raise PreclosePartialDailyPreviewError("Tamamlanmış günlük seri boş.")

    local_observed = _local_now(observed_at)
    _preclose_guard(local_observed)

    exchange_time = snapshot.exchange_time
    if exchange_time.tzinfo is None:
        exchange_time = exchange_time.replace(tzinfo=ISTANBUL)
    else:
        exchange_time = exchange_time.astimezone(ISTANBUL)

    if exchange_time.date() != local_observed.date():
        raise PreclosePartialDailyPreviewError(
            "Gün içi snapshot bugünkü seansa ait değil."
        )
    if snapshot.locked:
        raise PreclosePartialDailyPreviewError(
            "Gün içi snapshot veri kilidi altında."
        )
    if not snapshot.preview_only:
        # This capability is explicitly for a partial-session preview.
        raise PreclosePartialDailyPreviewError(
            "Pre-close overlay yalnız preview_only intraday snapshot kabul eder."
        )

    required = ("Open", "High", "Low", "Close", "Volume")
    missing = [column for column in required if column not in completed_daily.columns]
    if missing:
        raise PreclosePartialDailyPreviewError(
            "Günlük seride eksik OHLCV sütunları: " + ", ".join(missing)
        )

    values = (
        snapshot.day_open,
        snapshot.day_high,
        snapshot.day_low,
        snapshot.last_price,
        snapshot.cumulative_volume,
    )
    if any(float(value) <= 0 for value in values):
        raise PreclosePartialDailyPreviewError(
            "Partial OHLCV pozitif sayısal değerler içermelidir."
        )

    out = completed_daily.copy()
    today = local_observed.date()
    out = out.loc[_date_index(out) != today].copy()

    synthetic_index = pd.Timestamp(today)
    synthetic = pd.DataFrame(
        {
            "Open": [float(snapshot.day_open)],
            "High": [float(snapshot.day_high)],
            "Low": [float(snapshot.day_low)],
            "Close": [float(snapshot.last_price)],
            "Volume": [float(snapshot.cumulative_volume)],
        },
        index=[synthetic_index],
    )

    # Preserve any extra columns used by an upstream frame without inventing values.
    for column in out.columns:
        if column not in synthetic.columns:
            synthetic[column] = pd.NA
    synthetic = synthetic[out.columns]

    out = pd.concat([out, synthetic], axis=0).sort_index()
    return out


def build_preclose_overlay_fetcher(
    *,
    now: datetime,
    daily_fetcher: Callable[..., BatchMarketDataResult] = toplu_fiyat_verisi_getir,
    intraday_fetcher: Callable[..., ScheduledIntradayBatchResult] = (
        fetch_scheduled_intraday_batch
    ),
) -> Callable[..., BatchMarketDataResult]:
    """Bind a BatchStockScanner-compatible read-only partial-day data fetcher."""

    observed_at = _local_now(now)
    _preclose_guard(observed_at)

    def fetch(
        symbols: Iterable[str],
        *,
        islem_gunu: int = 160,
        indirme_donemi: str = "1y",
        **kwargs: object,
    ) -> BatchMarketDataResult:
        normalized = tuple(str(symbol) for symbol in symbols)

        daily = daily_fetcher(
            normalized,
            islem_gunu=islem_gunu,
            indirme_donemi=indirme_donemi,
            **kwargs,
        )
        intraday = intraday_fetcher(
            normalized,
            now=observed_at,
        )

        overlaid: dict[str, pd.DataFrame] = {}
        failures: list[BatchMarketDataFailure] = list(daily.hatalar)

        intraday_failure_by_symbol = {
            str(item.symbol): str(item.error)
            for item in intraday.failures
        }

        for symbol in normalized:
            daily_frame = daily.veriler.get(symbol)
            if daily_frame is None:
                continue

            snapshot = intraday.snapshots.get(symbol)
            if snapshot is None:
                failures.append(
                    BatchMarketDataFailure(
                        sembol=symbol,
                        hata=(
                            "PRECLOSE_INTRADAY_MISSING: "
                            + intraday_failure_by_symbol.get(
                                symbol,
                                "bugünkü partial snapshot yok",
                            )
                        ),
                    )
                )
                continue

            try:
                overlaid[symbol] = overlay_partial_daily_bar(
                    daily_frame,
                    snapshot,
                    observed_at=observed_at,
                )
            except PreclosePartialDailyPreviewError as error:
                failures.append(
                    BatchMarketDataFailure(
                        sembol=symbol,
                        hata=f"PRECLOSE_OVERLAY_BLOCKED: {error}",
                    )
                )

        # Preserve any additional fields on the canonical BatchMarketDataResult.
        return replace(
            daily,
            veriler=overlaid,
            hatalar=tuple(failures),
        )

    return fetch


def run_preclose_partial_preview(
    *,
    now: datetime | None = None,
    profile_name: str = "dengeli",
    result_limit: int = 50,
    daily_fetcher: Callable[..., BatchMarketDataResult] = toplu_fiyat_verisi_getir,
    intraday_fetcher: Callable[..., ScheduledIntradayBatchResult] = (
        fetch_scheduled_intraday_batch
    ),
) -> PreclosePreviewResult:
    """Run existing BIST scanner with a temporary partial-day overlay.

    The existing scanner, filter profile, BIST universe and StockAnalyzer are
    reused. The result is PREVIEW / NOT CANONICAL and is not persisted by this
    module.
    """

    observed_at = _local_now(now)
    _preclose_guard(observed_at)

    if not 1 <= int(result_limit) <= 100:
        raise PreclosePartialDailyPreviewError(
            "result_limit 1 ile 100 arasında olmalıdır."
        )

    overlay_fetcher = build_preclose_overlay_fetcher(
        now=observed_at,
        daily_fetcher=daily_fetcher,
        intraday_fetcher=intraday_fetcher,
    )
    scanner = BatchStockScanner(veri_getirici=overlay_fetcher)

    service = build_dashboard_market_scanner(
        now_provider=lambda: observed_at,
        tarayici=scanner,
    )

    request_kwargs: dict[str, object] = {
        "evren": "BIST Tüm",
        "profil_adi": profile_name,
        "maksimum_aday": int(result_limit),
        "internetten_evren_guncelle": False,
    }

    # Current production may expose optional sector context. Keep preview lean.
    fields = getattr(MarketScanRequest, "__dataclass_fields__", {})
    if "sektor_baglami_aktif" in fields:
        request_kwargs["sektor_baglami_aktif"] = False

    scan_result = service.calistir(MarketScanRequest(**request_kwargs))

    partial_count = sum(
        1
        for item in tuple(getattr(scan_result, "tum_sonuclar", ()) or ())
        if str(getattr(item, "analiz_tarihi", "")).startswith(
            observed_at.date().isoformat()
        )
    )
    if not partial_count:
        partial_count = sum(
            1
            for item in tuple(
                getattr(getattr(scan_result, "filtrelenmis", None), "adaylar", ())
                or ()
            )
            if str(getattr(item, "analiz_tarihi", "")).startswith(
                observed_at.date().isoformat()
            )
        )

    failure_count = len(
        tuple(getattr(getattr(scan_result, "filtrelenmis", None), "hatalar", ()) or ())
    )

    return PreclosePreviewResult(
        observed_at=observed_at,
        scan_result=scan_result,
        partial_symbol_count=partial_count,
        intraday_failure_count=failure_count,
    )


def preclose_preview_rows(
    result: PreclosePreviewResult,
) -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    candidates = tuple(result.scan_result.adaylar)

    for rank, candidate in enumerate(candidates, start=1):
        signal = getattr(candidate, "sinyal", None)
        risk = getattr(candidate, "risk_plani", None)
        rows.append(
            {
                "Sıra": rank,
                "Hisse": str(getattr(candidate, "sembol", "")).removesuffix(".IS"),
                "Preview skor": getattr(signal, "skor", None),
                "R/R": getattr(risk, "risk_odul_orani", None),
                "Hacim oranı": getattr(candidate, "hacim_orani", None),
                "Analiz tarihi": str(getattr(candidate, "analiz_tarihi", "")),
                "Durum": "PREVIEW · NOT CANONICAL · PARTIAL SESSION",
            }
        )

    return tuple(rows)