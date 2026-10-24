from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable, Iterable, Mapping

import pandas as pd

from backend.app.analysis.next_day_observation_memory import (
    list_final_outcome_records,
    list_frozen_selection_records,
    load_frozen_selection,
    persist_final_outcome,
)
from backend.app.analysis.next_day_outcome import evaluate_next_day_selection
from backend.app.analysis.ranking_memory import RankObservationJsonlStore
from backend.app.data.batch_market_data import (
    BatchMarketDataResult,
    toplu_fiyat_verisi_getir,
)

CONTRACT_ID = "NEXT_DAY_PHASE8_T1_OUTCOME_RUNTIME_ADAPTER_V1"

MarketDataFetcher = Callable[..., BatchMarketDataResult]


class NextDayOutcomeRuntimeError(RuntimeError):
    """T+1 outcome cannot be resolved without violating frozen contracts."""


@dataclass(frozen=True)
class NextDayOutcomeSettlement:
    canonical_date: str
    t1_date: str | None
    status: str
    detail: str = ""


def _clean_symbol(value: object) -> str:
    return str(value or "").strip().upper().removesuffix(".IS")


def _as_date(value: object) -> date | None:
    raw = str(value or "").strip()
    if len(raw) < 10:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def _column(frame: pd.DataFrame, name: str) -> object | None:
    target = name.casefold()
    for col in frame.columns:
        if str(col).casefold() == target:
            return col
    return None


def _rows_by_date(frame: object) -> dict[date, dict[str, float]]:
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return {}

    open_col = _column(frame, "Open")
    high_col = _column(frame, "High")
    low_col = _column(frame, "Low")
    close_col = _column(frame, "Close")
    if None in (open_col, high_col, low_col, close_col):
        return {}

    rows: dict[date, dict[str, float]] = {}
    for idx, row in frame.iterrows():
        try:
            day = pd.Timestamp(idx).date()
            open_ = float(row[open_col])
            high = float(row[high_col])
            low = float(row[low_col])
            close = float(row[close_col])
        except (TypeError, ValueError, KeyError):
            continue

        values = (open_, high, low, close)
        if any(v <= 0 or v != v or v in (float("inf"), float("-inf")) for v in values):
            continue
        if high < max(open_, low, close) or low > min(open_, high, close):
            continue

        rows[day] = {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
        }
    return rows


def _rank_universe_for_selection(
    *,
    canonical_date: str,
    selection_symbols: set[str],
    store: RankObservationJsonlStore,
) -> tuple[str, ...]:
    observations = tuple(
        item
        for item in store.list()
        if str(item.as_of)[:10] == canonical_date
    )
    if not observations:
        raise NextDayOutcomeRuntimeError("CANONICAL_RANK_UNIVERSE_MISSING")

    groups: dict[tuple[str, str, int], list[object]] = {}
    for item in observations:
        try:
            size = int(item.ranked_universe_size)
        except (TypeError, ValueError):
            continue
        key = (
            str(item.universe_source or ""),
            str(item.profile_name or ""),
            size,
        )
        groups.setdefault(key, []).append(item)

    eligible: list[tuple[tuple[str, str, int], tuple[object, ...]]] = []
    for key, items in groups.items():
        source, profile, expected_size = key
        if not source or not profile or expected_size <= 0:
            continue
        materialized = tuple(sorted(items, key=lambda x: (int(x.rank), str(x.symbol))))
        ranks = tuple(int(x.rank) for x in materialized)
        symbols = tuple(_clean_symbol(x.symbol) for x in materialized)
        if len(materialized) != expected_size:
            continue
        if ranks != tuple(range(1, expected_size + 1)):
            continue
        if len(set(symbols)) != expected_size:
            continue
        if not selection_symbols.issubset(set(symbols)):
            continue
        eligible.append((key, materialized))

    if len(eligible) != 1:
        raise NextDayOutcomeRuntimeError(
            f"CANONICAL_RANK_UNIVERSE_AMBIGUOUS_OR_INVALID:{len(eligible)}"
        )

    return tuple(_clean_symbol(x.symbol) for x in eligible[0][1])


def _normalize_market_result(
    result: BatchMarketDataResult,
) -> dict[str, dict[date, dict[str, float]]]:
    normalized: dict[str, dict[date, dict[str, float]]] = {}
    for raw_symbol, frame in dict(result.veriler or {}).items():
        symbol = _clean_symbol(raw_symbol)
        if not symbol:
            continue
        rows = _rows_by_date(frame)
        if rows:
            normalized[symbol] = rows
    return normalized


def _next_market_date(
    *,
    canonical_date: date,
    current_date: date,
    rows_by_symbol: Mapping[str, Mapping[date, object]],
) -> date | None:
    dates = sorted(
        {
            day
            for rows in rows_by_symbol.values()
            for day in rows.keys()
            if canonical_date < day <= current_date
        }
    )
    return dates[0] if dates else None


def _maps_for_dates(
    *,
    canonical_date: date,
    t1_date: date,
    rows_by_symbol: Mapping[str, Mapping[date, dict[str, float]]],
) -> tuple[dict[str, float], dict[str, dict[str, float]]]:
    closes: dict[str, float] = {}
    bars: dict[str, dict[str, float]] = {}
    for symbol, rows in rows_by_symbol.items():
        t_row = rows.get(canonical_date)
        t1_row = rows.get(t1_date)
        if t_row is not None:
            closes[symbol] = float(t_row["close"])
        if t1_row is not None:
            bars[symbol] = dict(t1_row)
    return closes, bars


def _pending_selection_dates(
    store: RankObservationJsonlStore,
) -> tuple[str, ...]:
    final_dates = {
        str(row.get("canonical_date", ""))
        for row in list_final_outcome_records(store)
    }
    frozen_dates = {
        str(row.get("canonical_date", ""))
        for row in list_frozen_selection_records(store)
    }
    return tuple(sorted(x for x in frozen_dates if x and x not in final_dates))


def settle_pending_next_day_outcomes(
    *,
    current_date: str,
    market_data_fetcher: MarketDataFetcher = toplu_fiyat_verisi_getir,
    store: RankObservationJsonlStore | None = None,
) -> tuple[NextDayOutcomeSettlement, ...]:
    """Settle frozen selections only when a real next market session is available.

    This is measurement-only:
    - no scanner
    - no BIST universe repository traversal
    - no selection mutation
    - no score/AL-SAT authority
    - no PENDING final write
    """

    memory = store or RankObservationJsonlStore()
    today = _as_date(current_date)
    if today is None:
        raise NextDayOutcomeRuntimeError("CURRENT_CANONICAL_DATE_INVALID")

    frozen_records = {
        str(row.get("canonical_date", "")): row
        for row in list_frozen_selection_records(memory)
    }

    settlements: list[NextDayOutcomeSettlement] = []

    for frozen_date in _pending_selection_dates(memory):
        t_date = _as_date(frozen_date)
        if t_date is None or t_date >= today:
            continue

        selection = load_frozen_selection(frozen_date, store=memory)
        if selection is None:
            continue

        selection_symbols = {
            _clean_symbol(item.symbol)
            for item in tuple(selection.primary) + tuple(selection.reserve)
            if _clean_symbol(item.symbol)
        }

        # Empty selection is legitimate NO FORCED FILL. There is no candidate
        # outcome to measure, so do not fabricate a benchmark-only final record.
        # NEXT_DAY_EMPTY_SELECTION_TERMINAL_OUTCOME_P0_V2
        # Empty Primary/Reserve is legitimate NO_FORCED_FILL.
        # Continue into canonical benchmark/T+1 evaluation; do not leave the session pending forever.

        try:
            universe_symbols = _rank_universe_for_selection(
                canonical_date=frozen_date,
                selection_symbols=selection_symbols,
                store=memory,
            )
        except NextDayOutcomeRuntimeError as exc:
            settlements.append(
                NextDayOutcomeSettlement(
                    canonical_date=frozen_date,
                    t1_date=None,
                    status="BLOCKED",
                    detail=str(exc),
                )
            )
            continue

        try:
            market = market_data_fetcher(
                universe_symbols,
                islem_gunu=40,
                indirme_donemi="3mo",
                bugun=today,
            )
        except Exception as exc:
            settlements.append(
                NextDayOutcomeSettlement(
                    canonical_date=frozen_date,
                    t1_date=None,
                    status="DATA_UNAVAILABLE",
                    detail=f"{type(exc).__name__}:{exc}",
                )
            )
            continue

        normalized = _normalize_market_result(market)
        t1 = _next_market_date(
            canonical_date=t_date,
            current_date=today,
            rows_by_symbol=normalized,
        )
        if t1 is None:
            settlements.append(
                NextDayOutcomeSettlement(
                    canonical_date=frozen_date,
                    t1_date=None,
                    status="WAITING_FOR_T1",
                )
            )
            continue

        universe_t_close, universe_t1_bars = _maps_for_dates(
            canonical_date=t_date,
            t1_date=t1,
            rows_by_symbol=normalized,
        )

        expected_digest = str(
            frozen_records.get(frozen_date, {}).get("selection_digest", "")
        ) or None

        try:
            outcome = evaluate_next_day_selection(
                selection,
                t1_date=t1.isoformat(),
                t_close_by_symbol=universe_t_close,
                t1_bars_by_symbol=universe_t1_bars,
                universe_t_close_by_symbol=universe_t_close,
                universe_t1_bars_by_symbol=universe_t1_bars,
                expected_selection_digest=expected_digest,
            )
        except Exception as exc:
            settlements.append(
                NextDayOutcomeSettlement(
                    canonical_date=frozen_date,
                    t1_date=t1.isoformat(),
                    status="BLOCKED",
                    detail=f"{type(exc).__name__}:{exc}",
                )
            )
            continue

        if (
            any(item.status == "PENDING" for item in outcome.outcomes)
            or outcome.primary.pending_count
            or outcome.reserve.pending_count
        ):
            settlements.append(
                NextDayOutcomeSettlement(
                    canonical_date=frozen_date,
                    t1_date=t1.isoformat(),
                    status="PENDING_DATA",
                    detail="Candidate T/T+1 data incomplete; final write suppressed.",
                )
            )
            continue

        try:
            persistence = persist_final_outcome(outcome, store=memory)
        except Exception as exc:
            settlements.append(
                NextDayOutcomeSettlement(
                    canonical_date=frozen_date,
                    t1_date=t1.isoformat(),
                    status="BLOCKED",
                    detail=f"{type(exc).__name__}:{exc}",
                )
            )
            continue

        settlements.append(
            NextDayOutcomeSettlement(
                canonical_date=frozen_date,
                t1_date=t1.isoformat(),
                status=persistence,
            )
        )

    return tuple(settlements)


__all__ = [
    "CONTRACT_ID",
    "NextDayOutcomeRuntimeError",
    "NextDayOutcomeSettlement",
    "settle_pending_next_day_outcomes",
]
