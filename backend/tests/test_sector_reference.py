from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from backend.app.analysis.sector_reference import (
    SectorReference,
    SectorReferenceError,
    build_company_ratio_references,
    compare_company_to_sector,
    references_from_csv_bytes,
    sector_comparison_rows,
)
from backend.app.models.fundamental_models import FinancialPeriod


def period(
    symbol: str,
    *,
    period_end: date = date(2026, 6, 30),
    quarter: int = 2,
    net_income: str = "100",
    equity: str = "1000",
) -> FinancialPeriod:
    return FinancialPeriod(
        symbol=symbol,
        period_end=period_end,
        fiscal_year=period_end.year,
        fiscal_quarter=quarter,
        currency="TRY",
        revenue="1000",
        gross_profit="400",
        operating_profit="200",
        ebitda="250",
        net_income=net_income,
        total_assets="2000",
        total_equity=equity,
        total_debt="500",
        cash_and_equivalents="100",
        current_assets="800",
        current_liabilities="400",
        operating_cash_flow="180",
        capital_expenditure="30",
        shares_outstanding="100",
    )


def test_sektor_referans_csv_okunur():
    content = (
        "symbol,sector,market_cap\n"
        "AAA,Bankacılık,2000\n"
        "BBB,Bankacılık,\n"
    ).encode("utf-8")

    result = references_from_csv_bytes(content)

    assert result["AAA"].sector == "Bankacılık"
    assert result["AAA"].market_cap == Decimal("2000")
    assert result["BBB"].market_cap is None


def test_tekrarlanan_sembol_reddedilir():
    content = (
        "symbol,sector\n"
        "AAA,Bankacılık\n"
        "AAA,Bankacılık\n"
    ).encode("utf-8")

    with pytest.raises(
        SectorReferenceError,
        match="Tekrarlanan",
    ):
        references_from_csv_bytes(content)


def test_guncel_sirket_oranlari_uretilir():
    references = {
        "AAA": SectorReference(
            "AAA",
            "Sanayi",
            Decimal("2000"),
        )
    }

    result = build_company_ratio_references(
        [period("AAA")],
        references,
        today=date(2026, 7, 31),
    )

    assert len(result) == 1
    assert result[0].price_to_earnings == Decimal("20.00")
    assert result[0].price_to_book == Decimal("2.00")
    assert result[0].current_ratio == Decimal("2.00")


def test_eski_bilanco_karsilastirmaya_alinmaz():
    references = {
        "AAA": SectorReference("AAA", "Sanayi")
    }

    result = build_company_ratio_references(
        [
            period(
                "AAA",
                period_end=date(2025, 6, 30),
            )
        ],
        references,
        today=date(2026, 7, 31),
    )

    assert result == ()


def test_negatif_karda_f_k_hesaplanmaz():
    references = {
        "AAA": SectorReference(
            "AAA",
            "Sanayi",
            Decimal("2000"),
        )
    }

    result = build_company_ratio_references(
        [period("AAA", net_income="-100")],
        references,
        today=date(2026, 7, 31),
    )

    assert result[0].price_to_earnings is None


def test_ayni_sektor_donem_ve_para_birimi_karsilastirilir():
    references = {
        "AAA": SectorReference(
            "AAA",
            "Sanayi",
            Decimal("2000"),
        ),
        "BBB": SectorReference(
            "BBB",
            "Sanayi",
            Decimal("3000"),
        ),
        "CCC": SectorReference(
            "CCC",
            "Sanayi",
            Decimal("4000"),
        ),
    }
    records = build_company_ratio_references(
        [
            period("AAA"),
            period("BBB", net_income="200"),
            period(
                "CCC",
                period_end=date(2026, 3, 31),
                quarter=1,
            ),
        ],
        references,
        today=date(2026, 7, 31),
    )

    comparison = compare_company_to_sector(records, "AAA")

    assert comparison.peer_count == 2
    assert comparison.period_key == "2026Q2"
    assert comparison.comparisons[0].metric == "F/K"


def test_sektor_medyanina_gore_konum_yazilir():
    references = {
        "AAA": SectorReference(
            "AAA",
            "Sanayi",
            Decimal("2000"),
        ),
        "BBB": SectorReference(
            "BBB",
            "Sanayi",
            Decimal("3000"),
        ),
    }
    records = build_company_ratio_references(
        [
            period("AAA", net_income="100"),
            period("BBB", net_income="300"),
        ],
        references,
        today=date(2026, 7, 31),
    )

    comparison = compare_company_to_sector(records, "AAA")
    rows = sector_comparison_rows(comparison)

    assert rows[0]["Şirket"] == Decimal("20.00")
    assert rows[0]["Sektör medyanı"] == Decimal("15.00")
    assert rows[0]["Konum"] == "Sektör medyanının üzerinde"


def test_tek_sirketle_sektor_karsilastirmasi_yapilmaz():
    references = {
        "AAA": SectorReference("AAA", "Sanayi")
    }
    records = build_company_ratio_references(
        [period("AAA")],
        references,
        today=date(2026, 7, 31),
    )

    with pytest.raises(
        SectorReferenceError,
        match="en az iki şirket",
    ):
        compare_company_to_sector(records, "AAA")
