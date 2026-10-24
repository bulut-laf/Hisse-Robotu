from datetime import date, datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from backend.app.analysis.daily_buy_decision_calibration import (
    build_buy_decision_calibration,
    buy_decision_calibration_rows,
)
from backend.app.analysis.daily_buy_decision_outcomes import (
    apply_session_prices,
    register_buy_decisions,
)

ISTANBUL = ZoneInfo("Europe/Istanbul")


def _decision(symbol: str, score: int = 78, volume: float = 1.35, rr: float = 1.8):
    return SimpleNamespace(
        symbol=symbol,
        priority=1,
        decision="AL",
        reference_price=100.0,
        technical_score=score,
        volume_ratio=volume,
        risk_reward=rr,
        rank_change=24,
        research_priority="HIGH",
        visibility_state="IMPROVING",
    )


def test_registration_persists_decision_context_for_calibration():
    records = register_buy_decisions(
        (),
        (_decision("AAA"),),
        now=datetime(2026, 8, 24, 9, 0, tzinfo=ISTANBUL),
    )
    item = records[0]
    assert item.technical_score == 78
    assert item.volume_ratio == 1.35
    assert item.risk_reward == 1.8
    assert item.rank_change == 24
    assert item.research_priority == "HIGH"
    assert item.visibility_state == "IMPROVING"


def test_calibration_stays_read_only_and_marks_small_samples_insufficient():
    records = register_buy_decisions(
        (),
        (_decision("AAA"),),
        now=datetime(2026, 8, 24, 9, 0, tzinfo=ISTANBUL),
    )
    records = apply_session_prices(records, {"AAA": 105.0}, observation_date=date(2026, 8, 25))
    slices = build_buy_decision_calibration(records)
    assert slices
    assert all(item.status == "YETERSİZ VERİ" for item in slices)


def test_calibration_can_flag_supportive_segment_after_minimum_sample():
    records = ()
    now = datetime(2026, 8, 24, 9, 0, tzinfo=ISTANBUL)
    for index in range(10):
        records = register_buy_decisions(records, (_decision(f"A{index}"),), now=now)
    records = apply_session_prices(
        records,
        {f"A{index}": 103.0 for index in range(10)},
        observation_date=date(2026, 8, 25),
    )
    slices = build_buy_decision_calibration(records)
    technical = next(
        item for item in slices
        if item.dimension == "Teknik skor" and item.segment == "70-79" and item.horizon == "1S"
    )
    assert technical.sample_size == 10
    assert technical.hit_rate == 100.0
    assert technical.status == "DESTEKLEYİCİ"


def test_rows_expose_dimension_segment_and_status():
    records = register_buy_decisions(
        (),
        (_decision("AAA"),),
        now=datetime(2026, 8, 24, 9, 0, tzinfo=ISTANBUL),
    )
    records = apply_session_prices(records, {"AAA": 101.0}, observation_date=date(2026, 8, 25))
    rows = buy_decision_calibration_rows(build_buy_decision_calibration(records))
    assert rows[0]["Boyut"]
    assert rows[0]["Segment"]
    assert rows[0]["Durum"] == "YETERSİZ VERİ"
