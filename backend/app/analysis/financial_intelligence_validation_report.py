from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Iterable

from .financial_intelligence_validation import (
    calibrate_score_separation,
    validate_point_in_time,
)
from ..models.investability_models import PointInTimeObservation


SCHEMA_VERSION = "fin-prod-v8-fin016-pit-validation-report-v1"
MODE = "READ_ONLY_POINT_IN_TIME_VALIDATION_AND_CALIBRATION"


@dataclass(frozen=True)
class PITLeakageIssue:
    index: int
    publication_date: str
    observation_date: str
    reason: str = "FUTURE_PUBLICATION_LEAKAGE"


def _dec(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def build_fin016_validation_report(
    observations: Iterable[PointInTimeObservation],
) -> dict:
    """Build a read-only FIN-016 validation report.

    Existing FIN-016 PIT/calibration functions remain authoritative.
    This layer only measures data usability and score separation.
    It never mutates weights, thresholds, AL/SAT, scanner, ranking or portfolio state.
    """
    rows = tuple(observations)
    leakage: list[PITLeakageIssue] = []

    usable = []
    incomplete = 0
    for idx, obs in enumerate(rows):
        if not validate_point_in_time(obs):
            leakage.append(
                PITLeakageIssue(
                    index=idx,
                    publication_date=obs.publication_date.isoformat(),
                    observation_date=obs.observation_date.isoformat(),
                )
            )
            continue
        if obs.score is None or obs.forward_return is None:
            incomplete += 1
            continue
        usable.append(obs)

    calibration = calibrate_score_separation(rows)

    blockers: list[str] = []
    if leakage:
        blockers.append("FUTURE_PUBLICATION_LEAKAGE")
    if not usable:
        blockers.append("NO_USABLE_POINT_IN_TIME_OBSERVATIONS")

    status = "PASS" if not blockers else "BLOCKED"

    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "mode": MODE,
        "read_only": True,
        "authoritative_scoring": "EXISTING_DETERMINISTIC_V1_UNCHANGED",
        "weight_optimization": False,
        "threshold_optimization": False,
        "input_observation_count": len(rows),
        "pit_usable_count": len(usable),
        "pit_incomplete_count": incomplete,
        "pit_leakage_count": len(leakage),
        "leakage_issues": [asdict(x) for x in leakage],
        "calibration": {
            "sample_size": calibration.sample_size,
            "usable_size": calibration.usable_size,
            "mean_forward_return": _dec(calibration.mean_forward_return),
            "high_score_mean_return": _dec(calibration.high_score_mean_return),
            "low_score_mean_return": _dec(calibration.low_score_mean_return),
            "separation": _dec(calibration.separation),
            "status": calibration.status,
        },
        "blockers": blockers,
        "rules": [
            "PUBLICATION_DATE_MUST_BE_LTE_OBSERVATION_DATE",
            "FUTURE_PUBLICATION_IS_EXCLUDED_AND_BLOCKING",
            "CALIBRATION_MEASURES_SEPARATION_ONLY",
            "NO_AUTO_WEIGHT_OPTIMIZATION",
            "NO_AUTO_THRESHOLD_OPTIMIZATION",
            "NO_AL_SAT_SCANNER_RANKING_PORTFOLIO_MUTATION",
        ],
    }
