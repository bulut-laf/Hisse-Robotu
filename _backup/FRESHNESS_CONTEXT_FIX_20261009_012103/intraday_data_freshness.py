from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from backend.app.data.delayed_data_pilot import DelayedDataSnapshot


DataFreshnessState = Literal[
    "DATA_GUNCEL",
    "DATA_GECIKMELI",
    "DATA_YETERSIZ",
    "DATA_KILITLI",
]


@dataclass(frozen=True)
class IntradayDataFreshness:
    symbol: str
    state: DataFreshnessState
    measured_delay_minutes: float | None
    missing_bar_count: int
    latest_bar_completed: bool
    locked: bool
    preview_only: bool
    reason: str


def evaluate_intraday_data_freshness(
    snapshot: DelayedDataSnapshot,
) -> IntradayDataFreshness:
    symbol = snapshot.symbol

    if snapshot.locked:
        return IntradayDataFreshness(
            symbol=symbol,
            state="DATA_KILITLI",
            measured_delay_minutes=snapshot.measured_delay_minutes,
            missing_bar_count=snapshot.missing_bar_count,
            latest_bar_completed=snapshot.latest_bar_completed,
            locked=True,
            preview_only=snapshot.preview_only,
            reason="Veri kilitli.",
        )

    if snapshot.measured_delay_minutes is None:
        return IntradayDataFreshness(
            symbol=symbol,
            state="DATA_YETERSIZ",
            measured_delay_minutes=None,
            missing_bar_count=snapshot.missing_bar_count,
            latest_bar_completed=snapshot.latest_bar_completed,
            locked=False,
            preview_only=snapshot.preview_only,
            reason="Gecikme olcumu yok.",
        )

    if snapshot.missing_bar_count > 0:
        return IntradayDataFreshness(
            symbol=symbol,
            state="DATA_YETERSIZ",
            measured_delay_minutes=snapshot.measured_delay_minutes,
            missing_bar_count=snapshot.missing_bar_count,
            latest_bar_completed=snapshot.latest_bar_completed,
            locked=False,
            preview_only=snapshot.preview_only,
            reason="Eksik 5m bar var.",
        )


    return IntradayDataFreshness(
        symbol=symbol,
        state="DATA_GUNCEL",
        measured_delay_minutes=snapshot.measured_delay_minutes,
        missing_bar_count=snapshot.missing_bar_count,
        latest_bar_completed=snapshot.latest_bar_completed,
        locked=False,
        preview_only=snapshot.preview_only,
        reason="Veri kullanilabilir.",
    )
