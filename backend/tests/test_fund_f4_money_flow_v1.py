from datetime import date, datetime, timezone
from decimal import Decimal

from backend.app.funds.contracts import (
    DataQualityState,
    FundDailyObservation,
)
from backend.app.funds.evidence_mapper import EvidenceState
from backend.app.funds.f4_snapshot import (
    detail_row_to_observation,
)
from backend.app.funds.f4_store_read_model import (
    f4_evidence_from_store,
    flow_metrics_from_store,
)
from backend.app.funds.store import (
    FundObservationJsonStore,
)


STAMP = datetime(
    2026,
    9,
    1,
    12,
    0,
    tzinfo=timezone.utc,
)

D1 = date(2026, 8, 31)
D2 = date(2026, 9, 1)


def observation(code, day, size, investors):
    return FundDailyObservation(
        canonical_fund_id=f"fund:tefas:{code}",
        observation_date=day,
        unit_price=Decimal("1"),
        fund_size=Decimal(size),
        investor_count=investors,
        shares_outstanding=None,
        daily_return=None,
        provider="TEFAS",
        fetched_at=STAMP,
        source_as_of=STAMP,
        data_quality_state=DataQualityState.VALID,
    )


def test_detail_schema_maps_exact_live_fields():
    item = detail_row_to_observation(
        {
            "fonKodu": "AAA",
            "sonFiyat": 1.25,
            "portBuyukluk": 1000000,
            "yatirimciSayi": 1000,
            "payAdet": 800000,
            "gunlukGetiri": 2.5,
        },
        expected_fund_code="AAA",
        fetched_at=STAMP,
        observation_date=D2,
    )

    assert item.canonical_fund_id == "fund:tefas:AAA"
    assert item.observation_date == D2
    assert item.fund_size == Decimal("1000000")
    assert item.investor_count == 1000
    assert item.shares_outstanding == Decimal("800000")
    assert item.daily_return == Decimal("0.025")


def test_default_observation_date_uses_utc_contract_date():
    item = detail_row_to_observation(
        {
            "fonKodu": "AAA",
            "sonFiyat": 1.25,
            "portBuyukluk": 1000000,
            "yatirimciSayi": 1000,
            "payAdet": 800000,
            "gunlukGetiri": 2.5,
        },
        expected_fund_code="AAA",
        fetched_at=STAMP,
    )

    assert item.observation_date == STAMP.date()


def test_positive_partial_f4():
    store = FundObservationJsonStore.__new__(
        FundObservationJsonStore
    )


def test_two_snapshots_produce_partial_positive_f4(tmp_path):
    store = FundObservationJsonStore(
        tmp_path / "observations.json"
    )

    store.upsert(
        (
            observation("AAA", D1, "100", 100),
            observation("AAA", D2, "110", 105),
        )
    )

    metric = flow_metrics_from_store(
        store
    )["fund:tefas:AAA"]

    assert metric.fund_size_change == Decimal("0.1")
    assert metric.investor_change == Decimal("0.05")
    assert metric.net_flow_ratio is None

    evidence = f4_evidence_from_store(
        store,
        canonical_fund_ids=("fund:tefas:AAA",),
    )["fund:tefas:AAA"]

    assert evidence.state is EvidenceState.POSITIVE
    assert evidence.missing_fields == ("net_flow_ratio",)


def test_two_negative_facts_produce_caution(tmp_path):
    store = FundObservationJsonStore(
        tmp_path / "observations.json"
    )

    store.upsert(
        (
            observation("AAA", D1, "100", 100),
            observation("AAA", D2, "90", 90),
        )
    )

    evidence = f4_evidence_from_store(
        store,
        canonical_fund_ids=("fund:tefas:AAA",),
    )["fund:tefas:AAA"]

    assert evidence.state is EvidenceState.CAUTION


def test_one_snapshot_keeps_f4_unavailable(tmp_path):
    store = FundObservationJsonStore(
        tmp_path / "observations.json"
    )

    store.upsert(
        (
            observation("AAA", D2, "100", 100),
        )
    )

    assert f4_evidence_from_store(
        store,
        canonical_fund_ids=("fund:tefas:AAA",),
    ) == {}


def test_history_only_rows_do_not_fake_f4(tmp_path):
    store = FundObservationJsonStore(
        tmp_path / "observations.json"
    )

    store.upsert(
        (
            FundDailyObservation(
                canonical_fund_id="fund:tefas:AAA",
                observation_date=D1,
                unit_price=Decimal("1"),
                fund_size=None,
                investor_count=None,
                shares_outstanding=None,
                daily_return=None,
                provider="TEFAS",
                fetched_at=STAMP,
                source_as_of=STAMP,
                data_quality_state=DataQualityState.PARTIAL,
            ),
            FundDailyObservation(
                canonical_fund_id="fund:tefas:AAA",
                observation_date=D2,
                unit_price=Decimal("1.1"),
                fund_size=None,
                investor_count=None,
                shares_outstanding=None,
                daily_return=None,
                provider="TEFAS",
                fetched_at=STAMP,
                source_as_of=STAMP,
                data_quality_state=DataQualityState.PARTIAL,
            ),
        )
    )

    assert flow_metrics_from_store(store) == {}
