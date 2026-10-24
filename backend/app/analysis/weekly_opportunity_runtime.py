from __future__ import annotations

from datetime import date
from typing import Iterable

from backend.app.analysis.next_day_selection import NextDayCandidateEvidence, NextDaySelectionResult
from backend.app.analysis.ranking_memory import RankObservationJsonlStore
from backend.app.analysis.weekly_opportunity import (
    WeeklyPricePlan,
    classify_weekly_opportunities,
)
from backend.app.analysis.weekly_opportunity_memory import persist_weekly_snapshot
from backend.app.analysis.weekly_opportunity_outcome import settle_weekly_outcomes

CONTRACT_ID = "WEEKLY_OPPORTUNITY_RUNTIME_V1"


def _clean(value: object) -> str:
    return str(value or "").upper().strip().removesuffix(".IS")


def _positive(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _read_attr(obj: object, *names: str) -> object | None:
    for name in names:
        if hasattr(obj, name):
            value = getattr(obj, name)
            if value is not None:
                return value
    return None


def price_plan_from_candidate(candidate: object) -> WeeklyPricePlan:
    risk = getattr(candidate, "risk_plani", None)
    current = _positive(_read_attr(candidate, "kapanis", "close", "current_price"))
    ideal = _positive(_read_attr(risk, "giris_fiyati", "entry_price")) if risk is not None else None
    stop = _positive(_read_attr(risk, "stop_loss", "stop_price")) if risk is not None else None
    target1 = _positive(_read_attr(risk, "hedef_fiyat", "target_price", "target_1")) if risk is not None else None
    target2 = _positive(_read_attr(risk, "hedef_2", "target_2")) if risk is not None else None
    rr = _positive(_read_attr(risk, "risk_odul_orani", "risk_reward_ratio")) if risk is not None else None

    # Explicit existing entry-zone contracts only. No range is synthesized.
    zone = _read_attr(candidate, "entry_zone", "giris_bolgesi")
    low = high = None
    if zone is not None:
        low = _positive(_read_attr(zone, "low", "lower", "min_price", "alt", "minimum"))
        high = _positive(_read_attr(zone, "high", "upper", "max_price", "ust", "maximum"))

    late = _positive(
        _read_attr(candidate, "late_entry_above", "maximum_entry", "max_entry_price")
    )

    return WeeklyPricePlan(
        current_price=current,
        entry_zone_low=low,
        entry_zone_high=high,
        ideal_entry=ideal,
        stop_loss=stop,
        target_1=target1,
        target_2=target2,
        risk_reward=rr,
        late_entry_above=late,
        source="EXISTING_STOCK_ANALYSIS_AND_RISK_PLAN",
    )


def _roles(selection: NextDaySelectionResult) -> dict[str, str]:
    result = {}
    for item in selection.primary:
        result[_clean(item.symbol)] = "PRIMARY"
    for item in selection.reserve:
        result[_clean(item.symbol)] = "RESERVE"
    return result


def observe_weekly_opportunity_runtime(
    *,
    scan_result: object,
    evidence: Iterable[NextDayCandidateEvidence],
    selection: NextDaySelectionResult,
    store: RankObservationJsonlStore | None = None,
) -> dict[str, object]:
    memory = store or RankObservationJsonlStore()
    materialized = tuple(evidence)
    if not materialized:
        return {"status": "NO_EVIDENCE"}

    canonical_date = materialized[0].canonical_date

    # Outcome settlement is measurement-only and may run every canonical session.
    settlement = settle_weekly_outcomes(
        current_date=canonical_date,
        store=memory,
    )

    try:
        canonical_day = date.fromisoformat(canonical_date)
    except ValueError:
        return {"status": "INVALID_CANONICAL_DATE", "settlement": settlement}

    # Weekly snapshot is frozen only on Friday canonical close.
    if canonical_day.weekday() != 4:
        return {"status": "NOT_FRIDAY", "settlement": settlement}

    current_results = tuple(getattr(scan_result, "tum_sonuclar", ()) or ())
    plans = {
        _clean(item.sembol): price_plan_from_candidate(item)
        for item in current_results
        if _clean(getattr(item, "sembol", ""))
    }

    result = classify_weekly_opportunities(
        materialized,
        price_plans=plans,
        next_day_roles=_roles(selection),
    )
    persistence = persist_weekly_snapshot(result, store=memory)
    return {
        "status": persistence,
        "canonical_date": canonical_date,
        "candidate_count": len(result.candidates),
        "w4_count": len(result.w4),
        "w3_count": len(result.w3),
        "w2_count": len(result.w2),
        "w1_count": len(result.w1),
        "settlement": settlement,
    }
