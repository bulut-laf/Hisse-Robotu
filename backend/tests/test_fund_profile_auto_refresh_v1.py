from datetime import date, datetime, timezone
from decimal import Decimal

from backend.app.funds.contracts import DataQualityState, FundDailyObservation
from backend.app.funds.fund_profile import build_fund_profile_read_model
from backend.app.funds.portfolio_tracking import FundPortfolioSnapshotJsonStore
from backend.app.funds.store import FundObservationJsonStore


STAMP = datetime(2026, 9, 4, 12, tzinfo=timezone.utc)


def obs(day: date, price: str, *, size: str | None = None, investors: int | None = None):
    return FundDailyObservation(
        canonical_fund_id="fund:tefas:AAA",
        observation_date=day,
        unit_price=Decimal(price),
        fund_size=None if size is None else Decimal(size),
        investor_count=investors,
        shares_outstanding=None,
        daily_return=None,
        provider="TEFAS",
        fetched_at=STAMP,
        source_as_of=STAMP,
        data_quality_state=DataQualityState.PARTIAL if size is None else DataQualityState.VALID,
    )


def test_profile_reads_latest_price_size_investors_and_returns(tmp_path):
    store = FundObservationJsonStore(tmp_path / "observations.json")
    portfolio = FundPortfolioSnapshotJsonStore(tmp_path / "portfolio.json")
    store.upsert((
        obs(date(2026, 1, 2), "1.00"),
        obs(date(2026, 3, 1), "1.10"),
        obs(date(2026, 6, 1), "1.20"),
        obs(date(2026, 8, 1), "1.30"),
        obs(date(2026, 9, 1), "1.40", size="1500000", investors=1250),
    ))

    profile = build_fund_profile_read_model(
        "fund:tefas:AAA",
        observation_store=store,
        portfolio_store=portfolio,
    )

    assert profile.fund_code == "AAA"
    assert profile.unit_price == Decimal("1.40")
    assert profile.fund_size == Decimal("1500000")
    assert profile.investor_count == 1250
    assert profile.returns["1A"] == Decimal("1.40") / Decimal("1.30") - Decimal("1")
    assert profile.returns["3A"] == Decimal("1.40") / Decimal("1.20") - Decimal("1")
    assert profile.returns["YTD"] is None
    assert profile.price_history[-1] == (date(2026, 9, 1), Decimal("1.40"))
    assert profile.fund_size_history[-1] == (date(2026, 9, 1), Decimal("1500000"))
    assert profile.investor_history[-1] == (date(2026, 9, 1), 1250)


def test_profile_invalid_id_fails_closed(tmp_path):
    store = FundObservationJsonStore(tmp_path / "observations.json")
    portfolio = FundPortfolioSnapshotJsonStore(tmp_path / "portfolio.json")
    try:
        build_fund_profile_read_model(
            "AAA",
            observation_store=store,
            portfolio_store=portfolio,
        )
    except ValueError as exc:
        assert str(exc) == "FUND_PROFILE_CANONICAL_ID_INVALID"
    else:
        raise AssertionError("invalid canonical id accepted")
