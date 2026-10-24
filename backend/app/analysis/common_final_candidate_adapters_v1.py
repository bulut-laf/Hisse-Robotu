"""Sprint-1 read-only adapters for the common final candidate list.

These adapters only normalize existing outputs. They do not run scans, fetch data,
change source ordering, create scores, or alter any AL/SAT decision.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from backend.app.analysis.common_final_candidate_selection_v1 import (
    CommonFinalCandidate,
    build_common_final_candidate_list,
)

_TECHNICAL_BASE = 10_000
_WEEKLY_BASE = 20_000
_MONTHLY_BASE = 30_000
_JUMP_BASE = 40_000


def _get(item: object, name: str, default: Any = None) -> Any:
    if isinstance(item, Mapping):
        return item.get(name, default)
    return getattr(item, name, default)


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _symbol(value: Any) -> str:
    return _text(value).upper().removesuffix(".IS")


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _enum_text(value: Any) -> str:
    return _text(getattr(value, "value", value))


def _join_text(*values: Any) -> str:
    parts: list[str] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, (tuple, list, set)):
            parts.extend(_text(x) for x in value if _text(x))
        elif _text(value):
            parts.append(_text(value))
    return " | ".join(dict.fromkeys(parts))


def adapt_morning_candidate_cards(cards: Iterable[object]) -> tuple[dict[str, Any], ...]:
    """Map MorningCandidateCard records while preserving their existing order."""
    rows: list[dict[str, Any]] = []
    for index, card in enumerate(cards, start=1):
        symbol = _symbol(_get(card, "symbol"))
        if not symbol:
            continue
        raw_source = _text(_get(card, "selection_source", "TARAMA")).upper()
        source = "SICRAMA" if raw_source == "SICRAMA" else "TEKNIK_TARAMA"
        native_rank = _number(_get(card, "rank"))
        rank = int(native_rank) if native_rank is not None else index
        base = _JUMP_BASE if source == "SICRAMA" else _TECHNICAL_BASE
        reasons = _join_text(
            _get(card, "selection_reason"),
            _get(card, "priority_reason"),
            _get(card, "positive_reasons", ()),
            _get(card, "risks", ()),
            _get(card, "jump_quality_reason"),
            _get(card, "entry_readiness_reason"),
        )
        status = _join_text(
            _get(card, "operational_status"),
            "VERİ ENGELİ" if bool(_get(card, "data_blocked", False)) else "",
        )
        rows.append({
            "symbol": symbol,
            "source": source,
            "horizon": "GUNLUK",
            "status": status,
            "reason": reasons,
            # Source base keeps technical/jump ranks from being confused with
            # weekly/monthly ranks. Native order remains intact within a source.
            "priority": base + rank,
            "technical_score": _number(_get(card, "technical_score")),
            "volume_ratio": _number(_get(card, "volume_ratio")),
            "risk_reward": _number(_get(card, "risk_reward")),
            "entry_readiness": _text(_get(card, "entry_readiness")),
            "data_status": "ENGELLI" if bool(_get(card, "data_blocked", False)) else "MEVCUT",
        })
    return tuple(rows)


def adapt_weekly_opportunity_candidates(result_or_candidates: object) -> tuple[dict[str, Any], ...]:
    """Map WeeklyOpportunityResult.candidates without turning stages into AL signals."""
    candidates = _get(result_or_candidates, "candidates", result_or_candidates)
    if candidates is None:
        return ()
    rows: list[dict[str, Any]] = []
    try:
        iterable = tuple(candidates)
    except TypeError:
        return ()
    for index, candidate in enumerate(iterable, start=1):
        symbol = _symbol(_get(candidate, "symbol"))
        if not symbol:
            continue
        native_rank = _number(_get(candidate, "research_rank"))
        rank = int(native_rank) if native_rank is not None else index
        state = _enum_text(_get(candidate, "state"))
        stage = _enum_text(_get(candidate, "stage"))
        plan = _get(candidate, "price_plan")
        reason = _join_text(
            _get(candidate, "why_visible_now"),
            _get(candidate, "what_must_happen_next"),
            _get(candidate, "what_invalidates_setup"),
            _get(candidate, "soft_contradictions", ()),
        )
        rows.append({
            "symbol": symbol,
            "source": "FIRSAT_RADARI_HAFTALIK",
            "horizon": "HAFTALIK",
            "status": _join_text(stage, state, _get(candidate, "pilot_research_status")),
            "reason": reason,
            "priority": _WEEKLY_BASE + rank,
            # Do not map research_rank or stage into a technical score.
            "technical_score": None,
            "volume_ratio": None,
            "risk_reward": _number(_get(plan, "risk_reward")),
            # Stage/status is not an entry-readiness decision.
            "entry_readiness": "",
            # These are research/next-day states, not data availability.
            "data_status": "",
        })
    return tuple(rows)


def _records(frame: object) -> tuple[dict[str, Any], ...]:
    if frame is None:
        return ()
    if hasattr(frame, "empty") and bool(getattr(frame, "empty")):
        return ()
    if hasattr(frame, "to_dict"):
        try:
            values = frame.to_dict(orient="records")
            return tuple(x for x in values if isinstance(x, Mapping))
        except (TypeError, ValueError):
            return ()
    if isinstance(frame, (tuple, list)):
        return tuple(x for x in frame if isinstance(x, Mapping))
    return ()


def _first(row: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        if name in row and row[name] is not None:
            return row[name]
    return None


def adapt_opportunity_radar_result(result: object) -> tuple[dict[str, Any], ...]:
    """Map the existing OpportunityRadarResult DataFrames as source evidence.

    Weekly Score and Aylık Skor remain source-specific reasons/status context;
    neither is mislabeled as the technical scan score.
    """
    rows: list[dict[str, Any]] = []

    weekly = _records(_get(result, "weekly"))
    for index, row in enumerate(weekly, start=1):
        symbol = _symbol(_first(row, "Hisse", "symbol", "Symbol"))
        if not symbol:
            continue
        native_rank = _number(_first(row, "Validated Öncelik", "Validated Oncelik", "Weekly Rank"))
        rank = int(native_rank) if native_rank is not None else index
        reason = _join_text(
            _first(row, "Durum", "Status"),
            "Weekly Score=" + _text(_first(row, "Weekly Score")) if _first(row, "Weekly Score") is not None else "",
            "Validated Quality=" + _text(_first(row, "Validated Quality")) if _first(row, "Validated Quality") is not None else "",
            "Validated Profile Count=" + _text(_first(row, "Validated Profile Count")) if _first(row, "Validated Profile Count") is not None else "",
        )
        rows.append({
            "symbol": symbol,
            "source": "FIRSAT_RADARI_HAFTALIK",
            "horizon": "HAFTALIK",
            "status": _text(_first(row, "Durum", "Status")),
            "reason": reason,
            "priority": _WEEKLY_BASE + rank,
            "technical_score": None,
            "volume_ratio": None,
            "risk_reward": None,
            "entry_readiness": "",
            # Radar Durum is a validation state, not a data-availability flag.
            "data_status": "",
        })

    for frame_name, label in (("monthly_strong", "AYLIK_GUCLU"), ("monthly_early", "AYLIK_ERKEN")):
        frame_rows = _records(_get(result, frame_name))
        for index, row in enumerate(frame_rows, start=1):
            symbol = _symbol(_first(row, "Hisse", "symbol", "Symbol"))
            if not symbol:
                continue
            monthly_score = _first(row, "Aylık Skor", "Aylik Skor", "Monthly Score")
            status = _text(_first(row, "Durum", "Status"))
            reason = _join_text(
                label,
                status,
                _first(row, "Aylık Sınıf", "Aylik Sinif", "Monthly Class"),
                "Aylık Skor=" + _text(monthly_score) if monthly_score is not None else "",
                _first(row, "Neden seçildi?", "Neden secildi?", "Reason"),
            )
            rows.append({
                "symbol": symbol,
                "source": "FIRSAT_RADARI_AYLIK",
                "horizon": "AYLIK",
                "status": _join_text(label, status),
                "reason": reason,
                "priority": _MONTHLY_BASE + index,
                "technical_score": None,
                "volume_ratio": None,
                "risk_reward": None,
                "entry_readiness": "",
                # Monthly Durum describes validation, not data availability.
                "data_status": "",
            })
    return tuple(rows)


def build_common_final_candidates(
    *,
    morning_cards: Iterable[object] = (),
    weekly_opportunities: object = (),
    opportunity_radar: object | None = None,
    limit: int | None = None,
) -> tuple[CommonFinalCandidate, ...]:
    """Build the common list from supplied existing outputs; no scanning or I/O."""
    normalized: list[dict[str, Any]] = []
    normalized.extend(adapt_morning_candidate_cards(morning_cards))
    normalized.extend(adapt_weekly_opportunity_candidates(weekly_opportunities))
    if opportunity_radar is not None:
        normalized.extend(adapt_opportunity_radar_result(opportunity_radar))
    return build_common_final_candidate_list(normalized, limit=limit)
