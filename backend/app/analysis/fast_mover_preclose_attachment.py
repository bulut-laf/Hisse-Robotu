"""Fast Mover Watch V1 pre-close raw-observation attachment.

This adapter is intentionally read-only. It does not evaluate production
Fast Mover thresholds. It only attaches current partial Research rank versus
the latest prior canonical Ranking Memory snapshot.

Authority:
- existing current scan result: READ
- Ranking Memory: READ
- no scanner invocation
- no persistence
- no canonical write
- no AL/SAT authority
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime

from backend.app.analysis.fast_mover_watch import FastMoverObservation
from backend.app.analysis.ranking_memory import (
    RankObservation,
    RankObservationJsonlStore,
)


def _clean_symbol(value: object) -> str:
    return str(value or "").removesuffix(".IS").upper().strip()


def _observation_date(value: object) -> date | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def _score(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _materialize_rank_history(
    rank_observations: object | None,
) -> tuple[RankObservation, ...]:
    if rank_observations is None:
        return tuple(RankObservationJsonlStore().list())
    return tuple(rank_observations)  # type: ignore[arg-type]


def _latest_prior_snapshot(
    observations: Iterable[RankObservation],
    *,
    observed_at: datetime,
    profile_name: str,
) -> dict[str, RankObservation]:
    target_date = observed_at.date()
    target_profile = str(profile_name or "").casefold().strip()

    eligible: list[RankObservation] = []
    for item in observations:
        item_date = _observation_date(item.as_of)
        if item_date is None or item_date >= target_date:
            continue
        if str(item.profile_name or "").casefold().strip() != target_profile:
            continue
        eligible.append(item)

    if not eligible:
        return {}

    latest_date = max(
        _observation_date(item.as_of)
        for item in eligible
        if _observation_date(item.as_of) is not None
    )

    result: dict[str, RankObservation] = {}
    for item in eligible:
        if _observation_date(item.as_of) != latest_date:
            continue
        symbol = _clean_symbol(item.symbol)
        if symbol:
            result[symbol] = item
    return result


def build_preclose_fast_mover_observations(
    *,
    current_results: Iterable[object],
    observed_at: datetime,
    profile_name: str,
    rank_observations: object | None = None,
) -> tuple[FastMoverObservation, ...]:
    """Attach raw current-vs-prior rank evidence.

    The order of existing ``tum_sonuclar`` is reused as the current Research
    order. The latest prior canonical snapshot for the same profile is the
    baseline. Same-day Ranking Memory observations are excluded because 17:20
    is partial / non-canonical.
    """

    current = tuple(current_results)
    current_universe_size = len(current)

    history = _materialize_rank_history(rank_observations)
    previous = _latest_prior_snapshot(
        history,
        observed_at=observed_at,
        profile_name=profile_name,
    )

    rows: list[FastMoverObservation] = []

    for current_rank, item in enumerate(current, start=1):
        symbol = _clean_symbol(getattr(item, "sembol", ""))
        if not symbol:
            continue

        prior = previous.get(symbol)
        signal = getattr(item, "sinyal", None)
        analysis_date = str(getattr(item, "analiz_tarihi", "") or "")

        rows.append(
            FastMoverObservation(
                symbol=symbol,
                current_rank=current_rank,
                previous_canonical_rank=(
                    int(prior.rank) if prior is not None else None
                ),
                current_universe_size=current_universe_size,
                previous_universe_size=(
                    int(prior.ranked_universe_size)
                    if prior is not None
                    else None
                ),
                data_usable=analysis_date.startswith(
                    observed_at.date().isoformat()
                ),
                baseline_comparable=bool(
                    prior is not None
                    and int(prior.ranked_universe_size) > 0
                    and current_universe_size > 0
                ),
                research_score_current=_score(
                    getattr(signal, "skor", None)
                ),
                research_score_previous=None,
                support_families=(),
                contradiction_families=(),
                early_visibility_overlap=False,
            )
        )

    return tuple(rows)


__all__ = ["build_preclose_fast_mover_observations"]