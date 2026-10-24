from datetime import date
from decimal import Decimal

from app.analysis.financial_intelligence_validation_report import (
    build_fin016_validation_report,
)
from app.models.investability_models import PointInTimeObservation


def D(v):
    return Decimal(str(v))


def test_fin016_report_blocks_future_publication_without_mutation():
    rows = (
        PointInTimeObservation(date(2026, 8, 1), date(2026, 8, 4), 80, D("0.10")),
        PointInTimeObservation(date(2026, 8, 5), date(2026, 8, 4), 40, D("-0.02")),
    )
    r = build_fin016_validation_report(rows)

    assert r["status"] == "BLOCKED"
    assert r["read_only"] is True
    assert r["pit_leakage_count"] == 1
    assert "FUTURE_PUBLICATION_LEAKAGE" in r["blockers"]
    assert r["weight_optimization"] is False
    assert r["threshold_optimization"] is False


def test_fin016_report_reuses_existing_positive_separation_contract():
    rows = tuple(
        PointInTimeObservation(
            date(2026, 8, 5),
            date(2026, 8, 4),
            80 if i % 2 == 0 else 40,
            D("0.05") if i % 2 == 0 else D("-0.01"),
        )
        for i in range(20)
    )
    r = build_fin016_validation_report(rows)

    assert r["status"] == "PASS"
    assert r["pit_usable_count"] == 20
    assert r["pit_leakage_count"] == 0
    assert r["calibration"]["status"] == "POSITIVE_SEPARATION"
    assert r["calibration"]["separation"] == "0.06"


def test_fin016_report_keeps_incomplete_observations_out_of_usable_count():
    rows = (
        PointInTimeObservation(date(2026, 8, 4), date(2026, 8, 4), None, None),
        PointInTimeObservation(date(2026, 8, 4), date(2026, 8, 4), 70, D("0.03")),
    )
    r = build_fin016_validation_report(rows)

    assert r["pit_incomplete_count"] == 1
    assert r["pit_usable_count"] == 1
