from datetime import date, datetime, timezone
from decimal import Decimal

from backend.app.funds.free_float_store import (
    FreeFloatJsonStore,
    FreeFloatRecord,
    FreeFloatSourceError,
    free_float_records_from_bytes,
    read_canonical_free_float,
)


def test_kap_record_roundtrip_and_latest_selection(tmp_path):
    store = FreeFloatJsonStore(tmp_path / "fdo.json")
    older = FreeFloatRecord(
        "THYAO", Decimal("100"), date(2026, 8, 1), "KAP",
        "https://www.kap.org.tr/tr/sirket-bilgileri/genel/x",
        datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    latest = FreeFloatRecord(
        "THYAO", Decimal("120"), date(2026, 9, 1), "KAP",
        "https://www.kap.org.tr/tr/sirket-bilgileri/genel/x",
        datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    result = store.upsert((older, latest))
    assert result.inserted == 2
    read = read_canonical_free_float(store, as_of=date(2026, 9, 4))
    assert read.source_state == "READY"
    assert read.shares_by_symbol["THYAO"] == Decimal("120")


def test_duplicate_is_idempotent(tmp_path):
    store = FreeFloatJsonStore(tmp_path / "fdo.json")
    record = FreeFloatRecord(
        "SAHOL", Decimal("50"), date(2026, 9, 1), "MKK", "mkk:official",
        datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    assert store.upsert((record,)).inserted == 1
    result = store.upsert((record,))
    assert result.inserted == 0
    assert result.unchanged == 1


def test_stale_record_is_fail_closed(tmp_path):
    store = FreeFloatJsonStore(tmp_path / "fdo.json")
    store.upsert((FreeFloatRecord(
        "TTKOM", Decimal("75"), date(2026, 1, 1), "KAP", "kap:old",
        datetime(2026, 1, 1, tzinfo=timezone.utc),
    ),))
    read = read_canonical_free_float(store, as_of=date(2026, 9, 4), max_age_days=45)
    assert read.source_state == "STALE"
    assert "TTKOM" in read.stale_symbols
    assert "TTKOM" not in read.shares_by_symbol


def test_noncanonical_source_rejected():
    try:
        FreeFloatRecord(
            "ASELS", Decimal("10"), date(2026, 9, 1), "YFINANCE", "x",
            datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
    except ValueError as exc:
        assert str(exc) == "FREE_FLOAT_SOURCE_NOT_CANONICAL"
    else:
        raise AssertionError("noncanonical source must be rejected")


def test_csv_import_accepts_kap_contract():
    raw = (
        b"symbol,free_float_shares,as_of,source,source_ref\n"
        b"SAHOL,12345,2026-09-01,KAP,https://www.kap.org.tr/tr/sirket-bilgileri/genel/x\n"
    )
    rows = free_float_records_from_bytes(
        raw,
        suffix=".csv",
        ingested_at=datetime(2026, 9, 4, tzinfo=timezone.utc),
    )
    assert rows[0].symbol == "SAHOL"
    assert rows[0].free_float_shares == Decimal("12345")


def test_import_without_canonical_fields_fails():
    try:
        free_float_records_from_bytes(b"symbol,free_float_shares\nSAHOL,10\n", suffix=".csv")
    except FreeFloatSourceError as exc:
        assert str(exc) == "FREE_FLOAT_IMPORT_NO_VALID_CANONICAL_RECORD"
    else:
        raise AssertionError("missing source contract must fail")
