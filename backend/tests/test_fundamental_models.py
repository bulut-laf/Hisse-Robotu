from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from backend.app.models.fundamental_models import (
    FinancialPeriod,
    FundamentalModelError,
)


def period(**overrides):
    values = {
        "symbol": "THYAO",
        "period_end": date(2026, 6, 30),
        "fiscal_year": 2026,
        "fiscal_quarter": 2,
        "currency": "TRY",
        "revenue": "1000",
        "gross_profit": "300",
        "operating_profit": "180",
        "ebitda": "220",
        "net_income": "120",
        "total_assets": "2500",
        "total_equity": "1000",
        "total_debt": "700",
        "cash_and_equivalents": "200",
        "current_assets": "900",
        "current_liabilities": "600",
        "operating_cash_flow": "160",
        "capital_expenditure": "40",
        "shares_outstanding": "100",
    }
    values.update(overrides)
    return FinancialPeriod(**values)


def test_finansal_donem_sembol_ve_para_birimini_normalize_eder():
    result = period(symbol=" thyao ", currency=" try ")

    assert result.symbol == "THYAO"
    assert result.currency == "TRY"
    assert result.revenue == Decimal("1000")
    assert result.period_key == "2026Q2"


def test_gecersiz_ceyrek_reddedilir():
    with pytest.raises(
        FundamentalModelError,
        match="Mali çeyrek",
    ):
        period(fiscal_quarter=5)


def test_pay_sayisi_sifir_olamaz():
    with pytest.raises(
        FundamentalModelError,
        match="pay sayısı",
    ):
        period(shares_outstanding="0")
