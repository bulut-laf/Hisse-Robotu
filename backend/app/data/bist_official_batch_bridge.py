from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Callable, Iterable
from zoneinfo import ZoneInfo

import pandas as pd

from .bist_official_archive import (
    archive_official_daily_snapshot,
    load_canonical_daily_snapshot,
)

ISTANBUL = ZoneInfo("Europe/Istanbul")
DEFAULT_ARCHIVE_ROOT = Path("data") / "bist_official_daily"


@dataclass(frozen=True)
class OfficialLatestDailyResult:
    islem_tarihi: date | None
    veriler: dict[str, pd.DataFrame]
    kaynak: str
    hatalar: tuple[str, ...] = ()


OfficialDailyLoader = Callable[
    [Iterable[str], date | None],
    OfficialLatestDailyResult,
]


def merge_official_daily_bar(
    historical: pd.DataFrame,
    official_daily: pd.DataFrame | None,
    *,
    max_rows: int | None = None,
) -> pd.DataFrame:
    """Yahoo tarihsel seri ile doğrulanmış resmî günlük barı birleştirir."""
    if historical is None or historical.empty:
        base = pd.DataFrame(
            columns=["Open", "High", "Low", "Close", "Volume"]
        )
    else:
        base = historical.copy()

    if official_daily is None or official_daily.empty:
        merged = base.sort_index()
        return merged.tail(max_rows).copy() if max_rows else merged

    official = official_daily.copy()

    for column in ("Open", "High", "Low", "Close", "Volume"):
        if column not in official.columns:
            raise ValueError(f"Resmî günlük veri kolonu eksik: {column}")

    if not isinstance(base.index, pd.DatetimeIndex):
        base.index = pd.to_datetime(base.index)
    if not isinstance(official.index, pd.DatetimeIndex):
        official.index = pd.to_datetime(official.index)

    official_dates = pd.DatetimeIndex(official.index).normalize()
    if len(official_dates) != len(set(official_dates)):
        raise ValueError("Resmî günlük veride aynı tarih birden fazla kez bulunuyor.")

    if not base.empty:
        base = base[
            ~pd.DatetimeIndex(base.index).normalize().isin(official_dates)
        ]

    merged = pd.concat([base, official], axis=0).sort_index()
    if merged.index.has_duplicates:
        raise ValueError("Birleştirilmiş OHLCV serisinde tekrarlı tarih oluştu.")

    return merged.tail(max_rows).copy() if max_rows else merged


def _candidate_dates(
    *,
    now: datetime | None = None,
    lookback_days: int = 10,
) -> tuple[date, ...]:
    if lookback_days < 1:
        raise ValueError("lookback_days en az 1 olmalıdır.")

    current = now or datetime.now(ISTANBUL)
    if current.tzinfo is None:
        current = current.replace(tzinfo=ISTANBUL)
    else:
        current = current.astimezone(ISTANBUL)

    first = (
        current.date()
        if current.time() >= time(18, 30)
        else current.date() - timedelta(days=1)
    )
    return tuple(first - timedelta(days=i) for i in range(lookback_days))


def _canonical_path(root: Path, trade_date: date) -> Path:
    return (
        root
        / "canonical"
        / f"{trade_date:%Y}"
        / f"{trade_date:%m}"
        / f"{trade_date.isoformat()}.csv"
    )


def load_latest_official_daily(
    symbols: Iterable[str],
    bugun: date | None = None,
    *,
    archive_root: Path | str = DEFAULT_ARCHIVE_ROOT,
    now: datetime | None = None,
    lookback_days: int = 10,
) -> OfficialLatestDailyResult:
    """En son tamamlanmış resmî günlük snapshot'ı arşivden veya BIST'ten yükler."""
    requested = tuple(
        str(x).strip().upper()
        for x in symbols
        if str(x).strip()
    )
    root = Path(archive_root)
    errors: list[str] = []

    if now is None and bugun is not None:
        now = datetime.combine(
            bugun,
            time(10, 0),
            tzinfo=ISTANBUL,
        )

    for trade_date in _candidate_dates(
        now=now,
        lookback_days=lookback_days,
    ):
        canonical = _canonical_path(root, trade_date)

        if canonical.exists():
            try:
                all_data = load_canonical_daily_snapshot(
                    trade_date,
                    archive_root=root,
                )
                selected = {
                    symbol: all_data[symbol]
                    for symbol in requested
                    if symbol in all_data
                }
                return OfficialLatestDailyResult(
                    islem_tarihi=trade_date,
                    veriler=selected,
                    kaynak="bist_resmi_arsiv",
                    hatalar=tuple(errors),
                )
            except Exception as exc:
                errors.append(
                    f"{trade_date.isoformat()} arşiv okuma: {exc}"
                )

        try:
            snapshot = archive_official_daily_snapshot(
                trade_date,
                archive_root=root,
                symbols=None,
            )
            all_data = load_canonical_daily_snapshot(
                trade_date,
                archive_root=root,
            )
            selected = {
                symbol: all_data[symbol]
                for symbol in requested
                if symbol in all_data
            }
            extra_errors = list(errors)
            if snapshot.gecersiz_semboller:
                extra_errors.append(
                    "resmî geçersiz barlar: "
                    + ", ".join(snapshot.gecersiz_semboller)
                )
            return OfficialLatestDailyResult(
                islem_tarihi=trade_date,
                veriler=selected,
                kaynak="bist_resmi_canli",
                hatalar=tuple(extra_errors),
            )
        except Exception as exc:
            errors.append(
                f"{trade_date.isoformat()} resmî bülten: {exc}"
            )

    return OfficialLatestDailyResult(
        islem_tarihi=None,
        veriler={},
        kaynak="bist_resmi_yok",
        hatalar=tuple(errors),
    )


__all__ = [
    "DEFAULT_ARCHIVE_ROOT",
    "OfficialDailyLoader",
    "OfficialLatestDailyResult",
    "load_latest_official_daily",
    "merge_official_daily_bar",
]
