from decimal import Decimal

from backend.app.funds.store import (
    FundObservationJsonStore,
)
from backend.app.funds.tefas_history_f3 import (
    price_series_from_tefas_history_rows,
)
from backend.app.funds.f3_production_population import (
    select_next_f3_batch,
)


def row(
    code,
    day,
    price,
):
    return {
        "fonKodu": code,
        "fonUnvan": "TEST",
        "kategoriDerece": 0,
        "kategoriFonSay": 29,
        "tarih": day,
        "fiyat": price,
    }


def universe(code):
    return {
        "fonkod": code,
    }


def test_invalid_price_is_missing_not_zero_fill():
    prices = price_series_from_tefas_history_rows(
        (
            row(
                "AAA",
                "2026-08-01",
                0,
            ),
            row(
                "AAA",
                "2026-08-02",
                "100",
            ),
            row(
                "AAA",
                "2026-08-03",
                "101",
            ),
            row(
                "AAA",
                "2026-08-04",
                "102",
            ),
        ),
        expected_fund_code="AAA",
    )

    assert prices == (
        Decimal("100"),
        Decimal("101"),
        Decimal("102"),
    )

    assert Decimal("0") not in prices


def test_missing_price_is_not_fabricated():
    prices = price_series_from_tefas_history_rows(
        (
            row(
                "AAA",
                "2026-08-01",
                None,
            ),
            row(
                "AAA",
                "2026-08-02",
                "100",
            ),
            row(
                "AAA",
                "2026-08-03",
                "101",
            ),
        ),
        expected_fund_code="AAA",
    )

    assert prices == (
        Decimal("100"),
        Decimal("101"),
    )


def test_malformed_price_is_not_fabricated():
    prices = price_series_from_tefas_history_rows(
        (
            row(
                "AAA",
                "2026-08-01",
                "bozuk",
            ),
            row(
                "AAA",
                "2026-08-02",
                "100",
            ),
            row(
                "AAA",
                "2026-08-03",
                "101",
            ),
            row(
                "AAA",
                "2026-08-04",
                "102",
            ),
        ),
        expected_fund_code="AAA",
    )

    assert prices == (
        Decimal("100"),
        Decimal("101"),
        Decimal("102"),
    )


def test_execution_local_exclusion_prevents_retry_starvation(
    tmp_path,
):
    store = FundObservationJsonStore(
        tmp_path / "observations.json"
    )

    selected = select_next_f3_batch(
        (
            universe("AP9"),
            universe("BDE"),
            universe("BFN"),
            universe("CCC"),
        ),
        store=store,
        batch_size=3,
        excluded_fund_codes=(
            "AP9",
            "BDE",
        ),
    )

    assert selected == (
        "BFN",
        "CCC",
    )
