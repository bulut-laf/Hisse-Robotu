from __future__ import annotations

from decimal import Decimal

from ..models.investability_models import CalibrationSummary, PointInTimeObservation


def validate_point_in_time(observation: PointInTimeObservation) -> bool:
    """True only when information was public by the observation date."""
    return observation.publication_date <= observation.observation_date


def filter_point_in_time(observations: tuple[PointInTimeObservation, ...]) -> tuple[PointInTimeObservation, ...]:
    return tuple(o for o in observations if validate_point_in_time(o))


def _mean(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    return sum(values, Decimal("0")) / Decimal(len(values))


def calibrate_score_separation(
    observations: tuple[PointInTimeObservation, ...],
    *,
    high_threshold: int = 70,
    low_threshold: int = 50,
) -> CalibrationSummary:
    valid = [o for o in observations if validate_point_in_time(o) and o.score is not None and o.forward_return is not None]
    all_returns = [o.forward_return for o in valid if o.forward_return is not None]
    high = [o.forward_return for o in valid if o.score is not None and o.score >= high_threshold and o.forward_return is not None]
    low = [o.forward_return for o in valid if o.score is not None and o.score <= low_threshold and o.forward_return is not None]
    high_m = _mean(high)
    low_m = _mean(low)
    separation = high_m - low_m if high_m is not None and low_m is not None else None
    if len(valid) < 20:
        status = "INSUFFICIENT_SAMPLE"
    elif separation is None:
        status = "INSUFFICIENT_BUCKETS"
    elif separation > 0:
        status = "POSITIVE_SEPARATION"
    else:
        status = "NO_POSITIVE_SEPARATION"
    return CalibrationSummary(len(observations), len(valid), _mean(all_returns), high_m, low_m, separation, status)
