"""Sprint-1: independent common final candidate list (V1).

This module deliberately does not import or modify the existing AL/SAT engine,
high-conviction gate, jump-quality gate, or entry-readiness evaluator.

Inputs are normalized candidate-like objects or dictionaries. Source adapters
can be wired in a later sprint after this module's contract is validated.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping


SOURCE_PRIORITY = {
    "TEKNIK_TARAMA": 10,
    "FIRSAT_RADARI_HAFTALIK": 20,
    "FIRSAT_RADARI_AYLIK": 30,
    "SICRAMA": 40,
}


def _value(item: object, name: str, default: Any = None) -> Any:
    if isinstance(item, Mapping):
        return item.get(name, default)
    return getattr(item, name, default)


def _clean(value: Any) -> str:
    return str(value or "").strip()


@dataclass(frozen=True)
class CandidateEvidence:
    source: str
    horizon: str = ""
    status: str = ""
    reason: str = ""


@dataclass(frozen=True)
class CommonFinalCandidate:
    symbol: str
    sources: tuple[str, ...]
    horizons: tuple[str, ...]
    evidence: tuple[CandidateEvidence, ...]
    priority: int
    technical_score: float | None
    volume_ratio: float | None
    risk_reward: float | None
    entry_readiness: str
    data_status: str
    reasons: tuple[str, ...]


def _number(item: object, name: str) -> float | None:
    raw = _value(item, name)
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def build_common_final_candidate_list(
    candidates: Iterable[object],
    *,
    limit: int | None = None,
) -> tuple[CommonFinalCandidate, ...]:
    """Merge normalized candidates by symbol without generating a new score.

    Expected fields:
      symbol (required), source, horizon, status, reason, priority,
      technical_score, volume_ratio, risk_reward, entry_readiness, data_status.

    Duplicate symbols are consolidated. Existing numeric values are retained
    as the maximum observed value for technical_score, volume_ratio and
    risk_reward; these are display/context fields, not a combined score.
    Lower numeric priority means earlier in the existing priority convention.
    Missing priority falls back to source order; source precedence only breaks
    ties and never upgrades an underlying AL/SAT decision.
    """
    grouped: dict[str, list[object]] = {}
    for item in candidates:
        symbol = _clean(_value(item, "symbol")).upper()
        if not symbol:
            continue
        grouped.setdefault(symbol, []).append(item)

    output: list[CommonFinalCandidate] = []
    for symbol, items in grouped.items():
        sources_seen: list[str] = []
        horizons_seen: list[str] = []
        evidence: list[CandidateEvidence] = []
        reasons: list[str] = []
        priorities: list[int] = []
        scores: list[float] = []
        volumes: list[float] = []
        risk_rewards: list[float] = []
        readiness_values: list[str] = []
        data_values: list[str] = []

        for item in items:
            source = _clean(_value(item, "source", "BILINMIYOR")).upper() or "BILINMIYOR"
            horizon = _clean(_value(item, "horizon")).upper()
            status = _clean(_value(item, "status")).upper()
            reason = _clean(_value(item, "reason"))
            if source not in sources_seen:
                sources_seen.append(source)
            if horizon and horizon not in horizons_seen:
                horizons_seen.append(horizon)
            evidence.append(CandidateEvidence(source, horizon, status, reason))
            if reason and reason not in reasons:
                reasons.append(reason)

            raw_priority = _value(item, "priority")
            try:
                if raw_priority is not None and raw_priority != "":
                    priorities.append(int(raw_priority))
            except (TypeError, ValueError):
                pass

            for field, bucket in (
                ("technical_score", scores),
                ("volume_ratio", volumes),
                ("risk_reward", risk_rewards),
            ):
                value = _number(item, field)
                if value is not None:
                    bucket.append(value)

            readiness = _clean(_value(item, "entry_readiness")).upper()
            if readiness and readiness not in readiness_values:
                readiness_values.append(readiness)
            data_status = _clean(_value(item, "data_status")).upper()
            if data_status and data_status not in data_values:
                data_values.append(data_status)

        # Use source priority only as a deterministic fallback/tie-breaker.
        fallback_priority = min(
            (SOURCE_PRIORITY.get(s, 999) for s in sources_seen),
            default=999,
        )
        priority = min(priorities) if priorities else fallback_priority
        output.append(
            CommonFinalCandidate(
                symbol=symbol,
                sources=tuple(sources_seen),
                horizons=tuple(horizons_seen),
                evidence=tuple(evidence),
                priority=priority,
                technical_score=max(scores) if scores else None,
                volume_ratio=max(volumes) if volumes else None,
                risk_reward=max(risk_rewards) if risk_rewards else None,
                entry_readiness=" | ".join(readiness_values),
                data_status=" | ".join(data_values),
                reasons=tuple(reasons),
            )
        )

    output.sort(
        key=lambda c: (
            c.priority,
            -SOURCE_PRIORITY.get(c.sources[0], 0) if c.sources else 0,
            c.symbol,
        )
    )
    if limit is not None:
        if limit < 0:
            raise ValueError("limit must be >= 0 or None")
        output = output[:limit]
    return tuple(output)
