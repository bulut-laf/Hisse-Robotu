from __future__ import annotations

from datetime import date

import pytest

from backend.app.data.fundamental_data import (
    CURRENT,
    FUTURE,
    STALE,
    FundamentalDataError,
    FundamentalFreshnessPolicy,
    evaluate_fundamental_freshness,
    periods_from_csv_bytes,
)


CSV_HEADER = (
    "symbol,period_end,fiscal_year,fiscal_quarter,currency,"
    "revenue,gross_profit,operating_profit,ebitda,net_income,"
    "total_assets,total_equity,total_debt,cash_and_equivalents,"
    "current_assets,current_liabilities,operating_cash_flow,"
    "capital_expenditure,shares_outstanding,source,published_at\n"
)


def csv_row(period_end="2026-06-30", quarter=2, fiscal_year=None):
    resolved_year = (
        int(period_end[:4])
        if fiscal_year is None
        else int(fiscal_year)
    )
    return (
        f"THYAO,{period_end},{resolved_year},{quarter},TRY,"
        "1000,300,180,200,100,2500,1000,700,200,"
        "900,600,160,40,100,KAP,2026-07-20\n"
    )


def test_csv_finansal_doneme_donusturulur():
    periods = periods_from_csv_bytes(
        (CSV_HEADER + csv_row()).encode("utf-8")
    )

    assert len(periods) == 1
    assert periods[0].symbol == "THYAO"
    assert periods[0].source == "KAP"
    assert periods[0].published_at == date(2026, 7, 20)


def test_eksik_csv_alani_reddedilir():
    payload = b"symbol,period_end\nTHYAO,2026-06-30\n"

    with pytest.raises(
        FundamentalDataError,
        match="Eksik bilanço alanları",
    ):
        periods_from_csv_bytes(payload)


def test_tekrarlanan_donem_reddedilir():
    payload = (
        CSV_HEADER + csv_row() + csv_row()
    ).encode("utf-8")

    with pytest.raises(
        FundamentalDataError,
        match="Tekrarlanan",
    ):
        periods_from_csv_bytes(payload)


def test_guncel_bilanco_kilidi_acmaz():
    periods = periods_from_csv_bytes(
        (CSV_HEADER + csv_row()).encode("utf-8")
    )

    result = evaluate_fundamental_freshness(
        periods,
        today=date(2026, 7, 30),
    )

    assert result.status == CURRENT
    assert result.locked is False


def test_eski_bilanco_kilitlenir():
    periods = periods_from_csv_bytes(
        (
            CSV_HEADER
            + csv_row(
                period_end="2025-06-30",
                quarter=2,
            )
        ).encode("utf-8")
    )

    result = evaluate_fundamental_freshness(
        periods,
        today=date(2026, 7, 30),
        policy=FundamentalFreshnessPolicy(
            maximum_age_days=190
        ),
    )

    assert result.status == STALE
    assert result.locked is True


def test_gelecek_tarihli_bilanco_kilitlenir():
    periods = periods_from_csv_bytes(
        (
            CSV_HEADER
            + csv_row(
                period_end="2026-12-31",
                quarter=4,
            )
        ).encode("utf-8")
    )

    result = evaluate_fundamental_freshness(
        periods,
        today=date(2026, 7, 30),
    )

    assert result.status == FUTURE
    assert result.locked is True
