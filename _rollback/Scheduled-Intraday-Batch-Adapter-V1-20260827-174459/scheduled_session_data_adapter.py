from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Callable
from zoneinfo import ZoneInfo

from backend.app.data.delayed_data_pilot import (
    DelayedDataPilotConfig,
    DelayedDataSnapshot,
    fetch_delayed_snapshot,
    normalize_symbol,
)

ISTANBUL = ZoneInfo("Europe/Istanbul")

PREOPEN = "PREOPEN"
POSTOPEN = "POSTOPEN"
PRECLOSE = "PRECLOSE"

VALID_PHASES = (PREOPEN, POSTOPEN, PRECLOSE)

POSTOPEN_START = time(10, 5)
PRECLOSE_START = time(17, 20)
PRECLOSE_END = time(18, 30)

# SCHEDULED_SESSION_DATA_ADAPTER_V1
# Read-only evidence adapter. No ranking/profile/AL-SAT write authority.


class ScheduledSessionDataAdapterError(ValueError):
    """Scheduled session evidence cannot be built safely."""


@dataclass(frozen=True)
class ScheduledSessionDataEvidence:
    symbol: str
    phase: str
    observed_at: datetime
    source_status: str
    source: str
    intraday_required: bool
    intraday_usable: bool
    gap_ready: bool
    locked: bool
    preview_only: bool
    last_price: float | None
    day_open: float | None
    day_high: float | None
    day_low: float | None
    cumulative_volume: float | None
    latest_bar_volume: float | None
    measured_delay_minutes: float | None
    gap_percent: float | None
    move_from_open_percent: float | None
    reason: str
    canonical_write_allowed: bool = False
    ranking_write_allowed: bool = False
    profile_write_allowed: bool = False
    al_sat_decision_allowed: bool = False


def _local_now(value: datetime | None) -> datetime:
    current = value or datetime.now(ISTANBUL)
    if current.tzinfo is None:
        return current.replace(tzinfo=ISTANBUL)
    return current.astimezone(ISTANBUL)


def _phase(value: str) -> str:
    normalized = str(value or "").strip().upper()
    if normalized not in VALID_PHASES:
        raise ScheduledSessionDataAdapterError(
            f"Geçersiz scheduled session phase: {value!r}"
        )
    return normalized


def _pct(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return round((numerator / denominator - 1.0) * 100.0, 4)


def _context_only(
    *,
    symbol: str,
    phase: str,
    observed_at: datetime,
    reason: str,
) -> ScheduledSessionDataEvidence:
    return ScheduledSessionDataEvidence(
        symbol=normalize_symbol(symbol),
        phase=phase,
        observed_at=observed_at,
        source_status="PREOPEN_CONTEXT_ONLY",
        source="none",
        intraday_required=False,
        intraday_usable=False,
        gap_ready=False,
        locked=False,
        preview_only=True,
        last_price=None,
        day_open=None,
        day_high=None,
        day_low=None,
        cumulative_volume=None,
        latest_bar_volume=None,
        measured_delay_minutes=None,
        gap_percent=None,
        move_from_open_percent=None,
        reason=reason,
    )


def _time_guard(
    *,
    phase: str,
    observed_at: datetime,
) -> str | None:
    clock = observed_at.timetz().replace(tzinfo=None)

    if phase == POSTOPEN and clock < POSTOPEN_START:
        return "POSTOPEN_TOO_EARLY"

    if phase == PRECLOSE and clock < PRECLOSE_START:
        return "PRECLOSE_TOO_EARLY"

    if phase == PRECLOSE and clock >= PRECLOSE_END:
        return "PRECLOSE_WINDOW_CLOSED"

    return None


def build_scheduled_session_data_evidence(
    symbol: str,
    *,
    phase: str,
    prior_close: float | None = None,
    now: datetime | None = None,
    config: DelayedDataPilotConfig | None = None,
    fetcher: Callable[..., DelayedDataSnapshot] = fetch_delayed_snapshot,
) -> ScheduledSessionDataEvidence:
    """Build read-only session evidence for scheduled operations.

    PREOPEN never invents an opening gap and does not call the intraday provider.
    POSTOPEN reuses the existing delayed 5m pilot and may calculate the real
    day-open gap when a valid prior close is supplied.
    PRECLOSE reuses the same pilot as preview-only evidence.

    This adapter has no authority to write Ranking Memory, Profile Memory,
    canonical scan state, or AL/SAT decisions.
    """

    normalized_phase = _phase(phase)
    observed_at = _local_now(now)

    if normalized_phase == PREOPEN:
        return _context_only(
            symbol=symbol,
            phase=normalized_phase,
            observed_at=observed_at,
            reason="08:45 yalnız seans öncesi bağlamdır; gerçek açılış gap'i henüz oluşmamıştır.",
        )

    guard = _time_guard(phase=normalized_phase, observed_at=observed_at)
    if guard is not None:
        return ScheduledSessionDataEvidence(
            symbol=normalize_symbol(symbol),
            phase=normalized_phase,
            observed_at=observed_at,
            source_status=guard,
            source="none",
            intraday_required=True,
            intraday_usable=False,
            gap_ready=False,
            locked=True,
            preview_only=True,
            last_price=None,
            day_open=None,
            day_high=None,
            day_low=None,
            cumulative_volume=None,
            latest_bar_volume=None,
            measured_delay_minutes=None,
            gap_percent=None,
            move_from_open_percent=None,
            reason=guard,
        )

    pilot_config = config or DelayedDataPilotConfig()
    snapshot = fetcher(
        symbol,
        config=pilot_config,
        now=observed_at,
    )

    same_day = snapshot.exchange_time.astimezone(ISTANBUL).date() == observed_at.date()
    usable = bool(
        same_day
        and not snapshot.locked
        and snapshot.last_price > 0
        and snapshot.day_open > 0
    )

    gap_percent = None
    gap_ready = False
    if (
        normalized_phase == POSTOPEN
        and prior_close is not None
        and float(prior_close) > 0
        and usable
    ):
        gap_percent = _pct(snapshot.day_open, float(prior_close))
        gap_ready = gap_percent is not None

    move_from_open = (
        _pct(snapshot.last_price, snapshot.day_open)
        if usable
        else None
    )

    if not same_day:
        reason = "INTRADAY_NOT_SAME_DAY"
    elif snapshot.locked:
        reason = "INTRADAY_SOURCE_LOCKED"
    elif normalized_phase == POSTOPEN and not gap_ready:
        reason = "POSTOPEN_EVIDENCE_READY_PRIOR_CLOSE_REQUIRED_FOR_GAP"
    elif normalized_phase == PRECLOSE:
        reason = "PRECLOSE_READ_ONLY_PREVIEW"
    else:
        reason = "POSTOPEN_GAP_ENTRY_EVIDENCE_READY"

    return ScheduledSessionDataEvidence(
        symbol=snapshot.symbol,
        phase=normalized_phase,
        observed_at=observed_at,
        source_status=snapshot.status,
        source=snapshot.source,
        intraday_required=True,
        intraday_usable=usable,
        gap_ready=gap_ready,
        locked=bool(snapshot.locked),
        preview_only=True,
        last_price=float(snapshot.last_price),
        day_open=float(snapshot.day_open),
        day_high=float(snapshot.day_high),
        day_low=float(snapshot.day_low),
        cumulative_volume=float(snapshot.cumulative_volume),
        latest_bar_volume=float(snapshot.latest_bar_volume),
        measured_delay_minutes=float(snapshot.measured_delay_minutes),
        gap_percent=gap_percent,
        move_from_open_percent=move_from_open,
        reason=reason,
    )