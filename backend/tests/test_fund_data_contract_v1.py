from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from backend.app.funds.contracts import DataQualityState, FundDailyObservation, to_primitive
from backend.app.funds.normalization import parse_decimal_tr, validate_allocation
from backend.app.funds.store import FundObservationJsonStore
from backend.app.funds.tefas_adapter import TefasProviderError, map_tefas_rows

UTC = timezone.utc
STAMP = datetime(2026, 9, 1, 9, 0, tzinfo=UTC)


def row(**changes):
    value = {"fund_code": " tst ", "fund_name": "  Türkçe   Fon ", "provider_fund_id": "tst",
             "category_id": "debt", "category_name": "Borçlanma Araçları", "currency": "try",
             "observation_date": "2026-08-31", "unit_price": "1,2500", "fund_size": "1.234,50",
             "investor_count": "1.005", "daily_return": "0,50%", "is_active": True}
    value.update(changes)
    return value


def mapped(**changes):
    return map_tefas_rows([row(**changes)], requested_at=STAMP, fetched_at=STAMP, source_as_of=STAMP)


def test_locale_normalization_preserves_zero_and_missing():
    assert parse_decimal_tr("0") == Decimal("0")
    assert parse_decimal_tr("") is None
    assert parse_decimal_tr("1.234,50") == Decimal("1234.50")
    assert parse_decimal_tr("0,50%", percent=True) == Decimal("0.005")
    with pytest.raises(ValueError):
        parse_decimal_tr("bozuk")


def test_fixture_maps_identity_and_daily_observation_deterministically():
    identity, observation = mapped()
    assert identity.fund_code == "TST" and identity.fund_name == "Türkçe Fon"
    assert observation.unit_price == Decimal("1.2500")
    assert observation.investor_count == 1005
    assert observation.data_quality_state is DataQualityState.VALID
    assert mapped() == mapped()


def test_partial_payload_is_not_filled():
    _, observation = mapped(unit_price=None)
    assert observation.unit_price is None
    assert observation.data_quality_state is DataQualityState.PARTIAL


def test_duplicate_and_future_observation_rejected():
    with pytest.raises(TefasProviderError, match="DUPLICATE"):
        map_tefas_rows([row(), row()], requested_at=STAMP, fetched_at=STAMP, source_as_of=STAMP)
    with pytest.raises(ValueError, match="leri"):
        mapped(observation_date="2999-01-01")


def test_timezone_is_explicit():
    item = mapped()[1]
    values = {name: getattr(item, name) for name in item.__dataclass_fields__}
    values["fetched_at"] = datetime(2026, 9, 1)
    with pytest.raises(ValueError, match="timezone-aware"):
        FundDailyObservation(**values)


def test_allocation_mismatch_is_not_silently_normalized():
    with pytest.raises(ValueError, match="100"):
        validate_allocation({"equity": Decimal("40"), "cash": Decimal("20")})


def test_store_is_idempotent_and_read_back_keeps_provenance(tmp_path):
    store = FundObservationJsonStore(tmp_path / "funds" / "observations.json")
    observation = mapped()[1]
    first = store.upsert([observation])
    second = store.upsert([observation])
    assert (first.inserted, second.unchanged, second.total_records) == (1, 1, 1)
    saved = store.list_records()[0]
    assert saved["provider"] == "TEFAS"
    assert saved["canonical_fund_id"].startswith("fund:tefas:")


def test_serialization_keeps_decimal_and_dates_exact():
    payload = to_primitive(mapped()[1])
    assert payload["unit_price"] == "1.2500"
    assert payload["observation_date"] == "2026-08-31"
    assert payload["record_type"] == "FundDailyObservation"
