from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from backend.app.data.delayed_data_pilot import DelayedDataSnapshot, fetch_delayed_snapshot


@dataclass(frozen=True, slots=True)
class ShadowPriceSuggestion:
    symbol: str
    price: float | None
    status: str
    locked: bool
    preview_only: bool
    source: str
    exchange_time: datetime
    received_time: datetime
    measured_delay_minutes: float

    @property
    def usable(self) -> bool:
        return not self.locked and self.price is not None and self.price > 0


def suggestion_from_snapshot(snapshot: DelayedDataSnapshot) -> ShadowPriceSuggestion:
    return ShadowPriceSuggestion(
        symbol=snapshot.symbol,
        price=None if snapshot.locked else float(snapshot.last_price),
        status=snapshot.status,
        locked=bool(snapshot.locked),
        preview_only=bool(snapshot.preview_only),
        source=snapshot.source,
        exchange_time=snapshot.exchange_time,
        received_time=snapshot.received_time,
        measured_delay_minutes=float(snapshot.measured_delay_minutes),
    )


def fetch_shadow_price_suggestion(
    symbol: str,
    *,
    fetcher: Callable[[str], DelayedDataSnapshot] = fetch_delayed_snapshot,
) -> ShadowPriceSuggestion:
    return suggestion_from_snapshot(fetcher(symbol))
