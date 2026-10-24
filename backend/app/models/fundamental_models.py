from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Mapping


class FundamentalModelError(ValueError):
    """Temel analiz veri modeli doğrulama hatası."""


def _decimal(value: object, field_name: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise FundamentalModelError(
            f"{field_name} sayısal olmalıdır."
        ) from exc
    if not result.is_finite():
        raise FundamentalModelError(
            f"{field_name} sonlu bir sayı olmalıdır."
        )
    return result


@dataclass(frozen=True)
class FinancialPeriod:
    """Tek bir finansal raporlama dönemini temsil eder."""

    symbol: str
    period_end: date
    fiscal_year: int
    fiscal_quarter: int
    currency: str
    revenue: Decimal
    gross_profit: Decimal
    operating_profit: Decimal
    ebitda: Decimal
    net_income: Decimal
    total_assets: Decimal
    total_equity: Decimal
    total_debt: Decimal
    cash_and_equivalents: Decimal
    current_assets: Decimal
    current_liabilities: Decimal
    operating_cash_flow: Decimal
    capital_expenditure: Decimal
    shares_outstanding: Decimal
    source: str = "manual"
    published_at: date | None = None

    def __post_init__(self) -> None:
        normalized_symbol = self.symbol.strip().upper()
        if not normalized_symbol:
            raise FundamentalModelError("Şirket sembolü boş olamaz.")
        if self.fiscal_quarter not in (1, 2, 3, 4):
            raise FundamentalModelError(
                "Mali çeyrek 1 ile 4 arasında olmalıdır."
            )
        if self.fiscal_year < 1900:
            raise FundamentalModelError("Mali yıl geçersiz.")
        if self.period_end.year not in (
            self.fiscal_year,
            self.fiscal_year + 1,
        ):
            raise FundamentalModelError(
                "Dönem sonu tarihi mali yılla uyumsuz."
            )
        if not self.currency.strip():
            raise FundamentalModelError("Para birimi boş olamaz.")

        decimal_fields = (
            "revenue",
            "gross_profit",
            "operating_profit",
            "ebitda",
            "net_income",
            "total_assets",
            "total_equity",
            "total_debt",
            "cash_and_equivalents",
            "current_assets",
            "current_liabilities",
            "operating_cash_flow",
            "capital_expenditure",
            "shares_outstanding",
        )
        for field_name in decimal_fields:
            object.__setattr__(
                self,
                field_name,
                _decimal(getattr(self, field_name), field_name),
            )

        if self.total_assets < 0:
            raise FundamentalModelError(
                "Toplam varlık negatif olamaz."
            )
        if self.total_debt < 0:
            raise FundamentalModelError(
                "Toplam borç negatif olamaz."
            )
        if self.cash_and_equivalents < 0:
            raise FundamentalModelError(
                "Nakit ve benzerleri negatif olamaz."
            )
        if self.shares_outstanding <= 0:
            raise FundamentalModelError(
                "Dolaşımdaki pay sayısı sıfırdan büyük olmalıdır."
            )

        object.__setattr__(self, "symbol", normalized_symbol)
        object.__setattr__(self, "currency", self.currency.strip().upper())
        object.__setattr__(self, "source", self.source.strip() or "manual")

    @property
    def period_key(self) -> str:
        return f"{self.fiscal_year}Q{self.fiscal_quarter}"


@dataclass(frozen=True)
class FundamentalRatios:
    symbol: str
    period_key: str
    gross_margin: Decimal | None
    operating_margin: Decimal | None
    ebitda_margin: Decimal | None
    net_margin: Decimal | None
    roe: Decimal | None
    roa: Decimal | None
    current_ratio: Decimal | None
    debt_to_equity: Decimal | None
    net_debt: Decimal
    net_debt_to_ebitda: Decimal | None
    free_cash_flow: Decimal
    free_cash_flow_margin: Decimal | None


@dataclass(frozen=True)
class FundamentalGrowth:
    symbol: str
    current_period_key: str
    comparison_period_key: str
    revenue_growth: Decimal | None
    ebitda_growth: Decimal | None
    net_income_growth: Decimal | None
    equity_growth: Decimal | None
    operating_cash_flow_growth: Decimal | None


@dataclass(frozen=True)
class FundamentalSnapshot:
    latest: FinancialPeriod
    previous_quarter: FinancialPeriod | None
    previous_year_same_quarter: FinancialPeriod | None
    ratios: FundamentalRatios
    quarter_growth: FundamentalGrowth | None
    annual_growth: FundamentalGrowth | None
    quality_flags: tuple[str, ...]
    source_metadata: Mapping[str, str]
