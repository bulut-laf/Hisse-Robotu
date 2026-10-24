from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from statistics import median
from typing import Iterable, Mapping

from .next_day_selection import (
    NextDayRole,
    NextDaySelectionItem,
    NextDaySelectionResult,
    STRATEGY_ID,
)


OUTCOME_CONTRACT_ID = "NEXT_DAY_T1_OUTCOME_V1"


@dataclass(frozen=True)
class T1Bar:
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class NextDayCandidateOutcome:
    evaluation_identity: str
    canonical_date: str
    t1_date: str
    symbol: str
    role: NextDayRole
    selection_order: int
    t_close: float | None
    t1_open: float | None
    t1_high: float | None
    t1_low: float | None
    t1_close: float | None
    close_to_close_return: float | None
    relative_return: float | None
    mfe: float | None
    mae: float | None
    benchmark_return: float
    status: str  # HIT / MISS / PENDING
    missing_reason: str | None = None


@dataclass(frozen=True)
class NextDayTierOutcomeSummary:
    role: NextDayRole
    candidate_count: int
    evaluated_count: int
    pending_count: int
    hit_count: int
    miss_count: int
    hit_rate: float | None
    median_relative_return: float | None
    average_relative_return: float | None
    median_mfe: float | None
    median_mae: float | None
    basket_success: bool | None


@dataclass(frozen=True)
class NextDayOutcomeResult:
    contract_id: str
    strategy_id: str
    canonical_date: str
    t1_date: str
    selection_digest: str
    benchmark_return: float
    outcomes: tuple[NextDayCandidateOutcome, ...]
    primary: NextDayTierOutcomeSummary
    reserve: NextDayTierOutcomeSummary
    primary_reserve_relative_spread: float | None


def _clean_symbol(value: object) -> str:
    return str(value or "").strip().upper().removesuffix(".IS")


def _finite_positive(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if result <= 0:
        return None
    if result != result or result in (float("inf"), float("-inf")):
        return None
    return result


def _normalize_bar(value: T1Bar | Mapping[str, object]) -> T1Bar | None:
    if isinstance(value, T1Bar):
        raw = value
    elif isinstance(value, Mapping):
        def pick(*names: str) -> object:
            for name in names:
                if name in value:
                    return value[name]
            return None

        raw = T1Bar(
            open=pick("open", "Open", "OPEN"),
            high=pick("high", "High", "HIGH"),
            low=pick("low", "Low", "LOW"),
            close=pick("close", "Close", "CLOSE"),
        )
    else:
        return None

    open_ = _finite_positive(raw.open)
    high = _finite_positive(raw.high)
    low = _finite_positive(raw.low)
    close = _finite_positive(raw.close)
    if None in (open_, high, low, close):
        return None

    assert open_ is not None
    assert high is not None
    assert low is not None
    assert close is not None

    if high < max(open_, low, close):
        return None
    if low > min(open_, high, close):
        return None
    return T1Bar(open=open_, high=high, low=low, close=close)


def _normalized_close_map(values: Mapping[str, object]) -> dict[str, float]:
    out: dict[str, float] = {}
    for raw_symbol, raw_value in values.items():
        symbol = _clean_symbol(raw_symbol)
        value = _finite_positive(raw_value)
        if symbol and value is not None:
            out[symbol] = value
    return out


def _normalized_bar_map(
    values: Mapping[str, T1Bar | Mapping[str, object]],
) -> dict[str, T1Bar]:
    out: dict[str, T1Bar] = {}
    for raw_symbol, raw_value in values.items():
        symbol = _clean_symbol(raw_symbol)
        bar = _normalize_bar(raw_value)
        if symbol and bar is not None:
            out[symbol] = bar
    return out


def _frozen_items(selection: NextDaySelectionResult) -> tuple[NextDaySelectionItem, ...]:
    return tuple(selection.primary) + tuple(selection.reserve)


def selection_freeze_payload(
    selection: NextDaySelectionResult,
) -> tuple[dict[str, object], ...]:
    """Canonical immutable payload used to detect later selection changes."""

    rows: list[dict[str, object]] = []
    for item in _frozen_items(selection):
        rows.append(
            {
                "strategy_id": selection.strategy_id,
                "canonical_date": item.canonical_date,
                "symbol": item.symbol,
                "role": item.role.value,
                "selection_order": int(item.selection_order),
                "research_rank": int(item.research_rank),
                "evidence_families": list(item.evidence_families),
                "contradiction_state": item.contradiction_state,
                "extension_state": item.extension_state.value,
                "rebound_state": item.rebound_state.value,
                "evaluation_identity": item.evaluation_identity,
            }
        )
    return tuple(rows)


def selection_digest(selection: NextDaySelectionResult) -> str:
    payload = selection_freeze_payload(selection)
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _return(t_close: float, t1_close: float) -> float:
    return (t1_close / t_close) - 1.0


def _benchmark_median(
    universe_t_close: Mapping[str, object],
    universe_t1_bars: Mapping[str, T1Bar | Mapping[str, object]],
) -> float:
    closes = _normalized_close_map(universe_t_close)
    bars = _normalized_bar_map(universe_t1_bars)
    returns = [
        _return(t_close, bars[symbol].close)
        for symbol, t_close in closes.items()
        if symbol in bars
    ]
    if not returns:
        raise ValueError(
            "canonical universe median benchmark cannot be built from supplied T/T+1 data"
        )
    return float(median(returns))


def _candidate_outcome(
    item: NextDaySelectionItem,
    *,
    t1_date: str,
    t_close_by_symbol: Mapping[str, float],
    t1_bar_by_symbol: Mapping[str, T1Bar],
    benchmark_return: float,
) -> NextDayCandidateOutcome:
    symbol = _clean_symbol(item.symbol)
    t_close = t_close_by_symbol.get(symbol)
    bar = t1_bar_by_symbol.get(symbol)

    if t_close is None:
        return NextDayCandidateOutcome(
            evaluation_identity=item.evaluation_identity,
            canonical_date=item.canonical_date,
            t1_date=t1_date,
            symbol=symbol,
            role=item.role,
            selection_order=item.selection_order,
            t_close=None,
            t1_open=bar.open if bar else None,
            t1_high=bar.high if bar else None,
            t1_low=bar.low if bar else None,
            t1_close=bar.close if bar else None,
            close_to_close_return=None,
            relative_return=None,
            mfe=None,
            mae=None,
            benchmark_return=benchmark_return,
            status="PENDING",
            missing_reason="T_CLOSE_MISSING",
        )

    if bar is None:
        return NextDayCandidateOutcome(
            evaluation_identity=item.evaluation_identity,
            canonical_date=item.canonical_date,
            t1_date=t1_date,
            symbol=symbol,
            role=item.role,
            selection_order=item.selection_order,
            t_close=t_close,
            t1_open=None,
            t1_high=None,
            t1_low=None,
            t1_close=None,
            close_to_close_return=None,
            relative_return=None,
            mfe=None,
            mae=None,
            benchmark_return=benchmark_return,
            status="PENDING",
            missing_reason="T1_BAR_MISSING_OR_INVALID",
        )

    close_return = _return(t_close, bar.close)
    relative = close_return - benchmark_return
    mfe = (bar.high / t_close) - 1.0
    mae = (bar.low / t_close) - 1.0
    status = "HIT" if close_return > benchmark_return else "MISS"

    return NextDayCandidateOutcome(
        evaluation_identity=item.evaluation_identity,
        canonical_date=item.canonical_date,
        t1_date=t1_date,
        symbol=symbol,
        role=item.role,
        selection_order=item.selection_order,
        t_close=t_close,
        t1_open=bar.open,
        t1_high=bar.high,
        t1_low=bar.low,
        t1_close=bar.close,
        close_to_close_return=close_return,
        relative_return=relative,
        mfe=mfe,
        mae=mae,
        benchmark_return=benchmark_return,
        status=status,
    )


def _summary(
    role: NextDayRole,
    rows: Iterable[NextDayCandidateOutcome],
) -> NextDayTierOutcomeSummary:
    materialized = tuple(row for row in rows if row.role is role)
    evaluated = tuple(
        row for row in materialized
        if row.status in {"HIT", "MISS"} and row.relative_return is not None
    )
    pending = len(materialized) - len(evaluated)
    hits = sum(1 for row in evaluated if row.status == "HIT")
    misses = sum(1 for row in evaluated if row.status == "MISS")

    if evaluated:
        relatives = [float(row.relative_return) for row in evaluated]
        mfes = [float(row.mfe) for row in evaluated if row.mfe is not None]
        maes = [float(row.mae) for row in evaluated if row.mae is not None]
        hit_rate = hits / len(evaluated)
        med_relative = float(median(relatives))
        avg_relative = float(sum(relatives) / len(relatives))
        med_mfe = float(median(mfes)) if mfes else None
        med_mae = float(median(maes)) if maes else None
        majority_needed = (len(evaluated) // 2) + 1
        basket_success = med_relative > 0 and hits >= majority_needed
    else:
        hit_rate = None
        med_relative = None
        avg_relative = None
        med_mfe = None
        med_mae = None
        basket_success = None

    return NextDayTierOutcomeSummary(
        role=role,
        candidate_count=len(materialized),
        evaluated_count=len(evaluated),
        pending_count=pending,
        hit_count=hits,
        miss_count=misses,
        hit_rate=hit_rate,
        median_relative_return=med_relative,
        average_relative_return=avg_relative,
        median_mfe=med_mfe,
        median_mae=med_mae,
        basket_success=basket_success,
    )


def evaluate_next_day_selection(
    selection: NextDaySelectionResult,
    *,
    t1_date: str,
    t_close_by_symbol: Mapping[str, object],
    t1_bars_by_symbol: Mapping[str, T1Bar | Mapping[str, object]],
    universe_t_close_by_symbol: Mapping[str, object],
    universe_t1_bars_by_symbol: Mapping[str, T1Bar | Mapping[str, object]],
    expected_selection_digest: str | None = None,
) -> NextDayOutcomeResult:
    """Evaluate a frozen Next-Day selection against T+1 realized prices.

    Main benchmark is the canonical-universe median close-to-close return.
    No trade P&L, AL/SAT decision, scanner, persistence, or new score is created.
    """

    if selection.strategy_id != STRATEGY_ID or not selection.strategy_frozen:
        raise ValueError("selection must use frozen NEXT_DAY_SELECTION_STRATEGY_V1")

    digest = selection_digest(selection)
    if expected_selection_digest is not None and digest != expected_selection_digest:
        raise ValueError("frozen selection digest mismatch")

    benchmark = _benchmark_median(
        universe_t_close_by_symbol,
        universe_t1_bars_by_symbol,
    )
    closes = _normalized_close_map(t_close_by_symbol)
    bars = _normalized_bar_map(t1_bars_by_symbol)

    rows = tuple(
        _candidate_outcome(
            item,
            t1_date=str(t1_date),
            t_close_by_symbol=closes,
            t1_bar_by_symbol=bars,
            benchmark_return=benchmark,
        )
        for item in _frozen_items(selection)
    )

    primary_summary = _summary(NextDayRole.PRIMARY, rows)
    reserve_summary = _summary(NextDayRole.RESERVE, rows)

    if (
        primary_summary.median_relative_return is not None
        and reserve_summary.median_relative_return is not None
    ):
        spread = (
            primary_summary.median_relative_return
            - reserve_summary.median_relative_return
        )
    else:
        spread = None

    return NextDayOutcomeResult(
        contract_id=OUTCOME_CONTRACT_ID,
        strategy_id=selection.strategy_id,
        canonical_date=selection.canonical_date,
        t1_date=str(t1_date),
        selection_digest=digest,
        benchmark_return=benchmark,
        outcomes=rows,
        primary=primary_summary,
        reserve=reserve_summary,
        primary_reserve_relative_spread=spread,
    )
