from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from backend.app.analysis.daily_buy_decision_outcomes import (
    BuyDecisionOutcomeJsonStore,
    apply_session_prices,
    buy_decision_hit_summary,
    register_buy_decisions,
)

ISTANBUL = ZoneInfo("Europe/Istanbul")


def _decision(symbol="AAA", priority=1, decision="AL", price=100.0):
    return SimpleNamespace(
        symbol=symbol,
        priority=priority,
        decision=decision,
        reference_price=price,
    )


def test_only_buy_decisions_are_registered_and_registration_is_idempotent():
    now = datetime(2026, 8, 24, 9, 0, tzinfo=ISTANBUL)
    records = register_buy_decisions(
        (),
        (_decision(), _decision("BBB", 2, "BEKLE", 50.0)),
        now=now,
    )
    assert len(records) == 1
    assert records[0].symbol == "AAA"
    again = register_buy_decisions(records, (_decision(),), now=now)
    assert len(again) == 1


def test_session_prices_build_1_3_5_session_returns():
    now = datetime(2026, 8, 24, 9, 0, tzinfo=ISTANBUL)
    records = register_buy_decisions((), (_decision(price=100.0),), now=now)
    for day, price in (
        (date(2026, 8, 25), 102.0),
        (date(2026, 8, 26), 101.0),
        (date(2026, 8, 27), 105.0),
        (date(2026, 8, 28), 104.0),
        (date(2026, 8, 31), 110.0),
    ):
        records = apply_session_prices(records, {"AAA": price}, observation_date=day)
    item = records[0]
    assert round(item.return_1s, 2) == 2.0
    assert round(item.return_3s, 2) == 5.0
    assert round(item.return_5s, 2) == 10.0


def test_same_observation_date_is_not_counted_twice():
    now = datetime(2026, 8, 24, 9, 0, tzinfo=ISTANBUL)
    records = register_buy_decisions((), (_decision(),), now=now)
    records = apply_session_prices(records, {"AAA": 101.0}, observation_date=date(2026, 8, 25))
    records = apply_session_prices(records, {"AAA": 103.0}, observation_date=date(2026, 8, 25))
    assert len(records[0].observations) == 1
    assert records[0].observations[0][1] == 101.0


def test_hit_summary_reports_positive_rate_and_average_return():
    now = datetime(2026, 8, 24, 9, 0, tzinfo=ISTANBUL)
    records = register_buy_decisions(
        (),
        (_decision("AAA", 1, price=100.0), _decision("BBB", 2, price=100.0)),
        now=now,
    )
    records = apply_session_prices(
        records,
        {"AAA": 105.0, "BBB": 95.0},
        observation_date=date(2026, 8, 25),
    )
    summary = buy_decision_hit_summary(records)
    one_session = summary[0]
    assert one_session["Değerlendirilen"] == 2
    assert one_session["Pozitif"] == 1
    assert one_session["İsabet (%)"] == 50.0
    assert one_session["Ortalama getiri (%)"] == 0.0


def test_store_round_trip(tmp_path: Path):
    store = BuyDecisionOutcomeJsonStore(tmp_path / "outcomes.json")
    records = register_buy_decisions(
        (),
        (_decision(),),
        now=datetime(2026, 8, 24, 9, 0, tzinfo=ISTANBUL),
    )
    store.save(records)
    loaded = store.load()
    assert loaded == records
