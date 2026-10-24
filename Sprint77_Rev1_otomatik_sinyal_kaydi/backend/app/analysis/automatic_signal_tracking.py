from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Callable, Iterable

import pandas as pd
import yfinance as yf

from .signal_outcome_tracking import (
    SignalOutcome,
    SignalOutcomeError,
    SignalOutcomeJsonStore,
    SignalSnapshot,
    evaluate_signal,
)


class AutomaticSignalTrackingError(ValueError):
    """Otomatik sinyal kaydı veya sonuç güncellemesi tamamlanamadı."""


@dataclass(frozen=True)
class AutomaticSignalSaveResult:
    outcome: SignalOutcome
    created: bool
    updated: bool
    path_name: str


@dataclass(frozen=True)
class AutomaticSignalUpdateSummary:
    total_records: int
    updated_records: int
    unchanged_records: int
    failed_records: int
    pending_horizons: int
    completed_horizons: int
    errors: tuple[str, ...]


def normalize_symbol(symbol: str) -> str:
    cleaned = symbol.strip().upper().removeprefix("﻿")
    if not cleaned:
        raise AutomaticSignalTrackingError("Sembol boş olamaz.")
    if not cleaned.endswith(".IS"):
        cleaned += ".IS"
    return cleaned


def _normalize_price_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        raise AutomaticSignalTrackingError("Fiyat verisi bulunamadı.")

    normalized = frame.copy()
    if isinstance(normalized.columns, pd.MultiIndex):
        normalized.columns = normalized.columns.get_level_values(0)

    required = {"Close", "High", "Low"}
    missing = required - set(normalized.columns)
    if missing:
        raise AutomaticSignalTrackingError(
            "Eksik fiyat sütunları: " + ", ".join(sorted(missing))
        )

    normalized = normalized.loc[:, ["Close", "High", "Low"]].copy()
    normalized.index = pd.to_datetime(normalized.index).tz_localize(None)
    normalized = normalized.sort_index()
    normalized = normalized[
        ~normalized.index.duplicated(keep="last")
    ]

    for column in normalized.columns:
        normalized[column] = pd.to_numeric(
            normalized[column],
            errors="coerce",
        )

    normalized = normalized.dropna()
    if normalized.empty:
        raise AutomaticSignalTrackingError(
            "Fiyat verisi kullanılabilir kayıt içermiyor."
        )
    return normalized


def fetch_signal_price_history(
    symbol: str,
    *,
    start_date: date,
    end_date: date | None = None,
    downloader: Callable[..., pd.DataFrame] = yf.download,
) -> pd.DataFrame:
    normalized_symbol = normalize_symbol(symbol)
    resolved_end = end_date or date.today()
    query_end = resolved_end + timedelta(days=1)

    try:
        raw = downloader(
            tickers=normalized_symbol,
            start=start_date.isoformat(),
            end=query_end.isoformat(),
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=False,
            timeout=30,
        )
    except Exception as error:
        raise AutomaticSignalTrackingError(
            f"{normalized_symbol} fiyat verisi alınamadı: {error}"
        ) from error

    return _normalize_price_frame(raw)


def _record_key(snapshot: SignalSnapshot) -> tuple[str, date]:
    return snapshot.symbol, snapshot.signal_date


def find_existing_outcome(
    outcomes: Iterable[SignalOutcome],
    snapshot: SignalSnapshot,
) -> SignalOutcome | None:
    key = _record_key(snapshot)
    for outcome in outcomes:
        if _record_key(outcome.snapshot) == key:
            return outcome
    return None


def _completed_count(outcome: SignalOutcome) -> int:
    return sum(item.available for item in outcome.horizons)


def save_or_update_signal(
    snapshot: SignalSnapshot,
    price_frame: pd.DataFrame,
    *,
    store: SignalOutcomeJsonStore,
) -> AutomaticSignalSaveResult:
    frame = _normalize_price_frame(price_frame)
    current = find_existing_outcome(store.list(), snapshot)
    evaluated = evaluate_signal(snapshot, frame)

    if current is None:
        path = store.save(evaluated)
        return AutomaticSignalSaveResult(
            outcome=evaluated,
            created=True,
            updated=False,
            path_name=path.name,
        )

    preserved_snapshot = current.snapshot
    refreshed = evaluate_signal(preserved_snapshot, frame)

    current_completed = _completed_count(current)
    refreshed_completed = _completed_count(refreshed)

    if refreshed_completed <= current_completed:
        return AutomaticSignalSaveResult(
            outcome=current,
            created=False,
            updated=False,
            path_name=f"{current.snapshot.record_id}.json",
        )

    path = store.save(refreshed)
    return AutomaticSignalSaveResult(
        outcome=refreshed,
        created=False,
        updated=True,
        path_name=path.name,
    )


def automatic_record_from_values(
    *,
    symbol: str,
    signal_date: date,
    reference_price: float,
    decision_class: str,
    quality_score: int,
    daily_direction: str,
    weekly_direction: str,
    store: SignalOutcomeJsonStore,
    divergence_type: str = "",
    market_regime: str = "",
    sector: str = "",
    momentum_state: str = "",
    volume_confirmation: bool | None = None,
    atr_percent: float | None = None,
    risk_reward_ratio: float | None = None,
    stop_loss: float | None = None,
    target_1: float | None = None,
    target_2: float | None = None,
    downloader: Callable[..., pd.DataFrame] = yf.download,
    today: date | None = None,
) -> AutomaticSignalSaveResult:
    snapshot = SignalSnapshot(
        symbol=symbol,
        signal_date=signal_date,
        reference_price=reference_price,
        decision_class=decision_class,
        quality_score=quality_score,
        daily_direction=daily_direction,
        weekly_direction=weekly_direction,
        divergence_type=divergence_type,
        market_regime=market_regime,
        sector=sector,
        momentum_state=momentum_state,
        volume_confirmation=volume_confirmation,
        atr_percent=atr_percent,
        risk_reward_ratio=risk_reward_ratio,
        stop_loss=stop_loss,
        target_1=target_1,
        target_2=target_2,
    )

    frame = fetch_signal_price_history(
        snapshot.symbol,
        start_date=signal_date,
        end_date=today or date.today(),
        downloader=downloader,
    )
    return save_or_update_signal(
        snapshot,
        frame,
        store=store,
    )


def update_all_signal_outcomes(
    *,
    store: SignalOutcomeJsonStore,
    downloader: Callable[..., pd.DataFrame] = yf.download,
    today: date | None = None,
) -> AutomaticSignalUpdateSummary:
    records = store.list()
    updated = 0
    unchanged = 0
    failed = 0
    errors: list[str] = []

    for outcome in records:
        try:
            frame = fetch_signal_price_history(
                outcome.snapshot.symbol,
                start_date=outcome.snapshot.signal_date,
                end_date=today or date.today(),
                downloader=downloader,
            )
            refreshed = evaluate_signal(outcome.snapshot, frame)
            if _completed_count(refreshed) > _completed_count(outcome):
                store.save(refreshed)
                updated += 1
            else:
                unchanged += 1
        except (
            AutomaticSignalTrackingError,
            SignalOutcomeError,
            ValueError,
            TypeError,
            OSError,
        ) as error:
            failed += 1
            errors.append(
                f"{outcome.snapshot.symbol} · "
                f"{outcome.snapshot.signal_date}: {error}"
            )

    final_records = store.list()
    pending = sum(
        not horizon.available
        for outcome in final_records
        for horizon in outcome.horizons
    )
    completed = sum(
        horizon.available
        for outcome in final_records
        for horizon in outcome.horizons
    )

    return AutomaticSignalUpdateSummary(
        total_records=len(records),
        updated_records=updated,
        unchanged_records=unchanged,
        failed_records=failed,
        pending_horizons=pending,
        completed_horizons=completed,
        errors=tuple(errors),
    )
