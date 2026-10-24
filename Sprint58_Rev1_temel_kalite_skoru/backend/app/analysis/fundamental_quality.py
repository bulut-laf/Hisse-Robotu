from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Mapping, TypeVar

from ..data.fundamental_data import FundamentalFreshnessResult
from ..models.fundamental_models import FundamentalSnapshot


@dataclass(frozen=True)
class FundamentalQualityComponent:
    name: str
    score: int
    maximum_score: int
    reasons: tuple[str, ...]
    risks: tuple[str, ...]


@dataclass(frozen=True)
class FundamentalQualityScore:
    symbol: str
    period_key: str
    total_score: int | None
    profitability: FundamentalQualityComponent
    growth: FundamentalQualityComponent
    leverage: FundamentalQualityComponent
    liquidity: FundamentalQualityComponent
    cash_flow: FundamentalQualityComponent
    locked: bool
    explanation: str

    @property
    def grade(self) -> str:
        if self.total_score is None:
            return "Hesaplanamadı"
        if self.total_score >= 80:
            return "Güçlü"
        if self.total_score >= 65:
            return "İyi"
        if self.total_score >= 50:
            return "Orta"
        return "Zayıf"


def _component(
    name: str,
    maximum: int,
    rules: Iterable[tuple[bool, int, str, str]],
) -> FundamentalQualityComponent:
    score = 0
    reasons: list[str] = []
    risks: list[str] = []

    for condition, points, positive, negative in rules:
        if condition:
            score += points
            reasons.append(positive)
        else:
            risks.append(negative)

    return FundamentalQualityComponent(
        name=name,
        score=min(score, maximum),
        maximum_score=maximum,
        reasons=tuple(reasons),
        risks=tuple(risks),
    )


def calculate_fundamental_quality(
    snapshot: FundamentalSnapshot,
    freshness: FundamentalFreshnessResult,
) -> FundamentalQualityScore:
    ratios = snapshot.ratios
    latest = snapshot.latest

    empty = FundamentalQualityComponent("", 0, 0, (), ())

    if freshness.locked:
        return FundamentalQualityScore(
            symbol=latest.symbol,
            period_key=latest.period_key,
            total_score=None,
            profitability=empty,
            growth=empty,
            leverage=empty,
            liquidity=empty,
            cash_flow=empty,
            locked=True,
            explanation=(
                "Bilanço tazelik kilidi aktif; temel kalite skoru "
                "üretilmedi."
            ),
        )

    required = (
        ratios.net_margin,
        ratios.roe,
        ratios.current_ratio,
        ratios.debt_to_equity,
        ratios.net_debt_to_ebitda,
        ratios.free_cash_flow_margin,
    )
    if any(value is None for value in required):
        return FundamentalQualityScore(
            symbol=latest.symbol,
            period_key=latest.period_key,
            total_score=None,
            profitability=empty,
            growth=empty,
            leverage=empty,
            liquidity=empty,
            cash_flow=empty,
            locked=True,
            explanation=(
                "Temel kalite skoru için gerekli finansal oranların "
                "tamamı hesaplanamadı."
            ),
        )

    profitability = _component(
        "Kârlılık",
        25,
        (
            (
                ratios.net_margin >= Decimal("10"),
                8,
                "Net kâr marjı en az %10.",
                "Net kâr marjı %10 altında.",
            ),
            (
                ratios.roe >= Decimal("15"),
                7,
                "ROE en az %15.",
                "ROE %15 altında.",
            ),
            (
                ratios.roa is not None
                and ratios.roa >= Decimal("5"),
                5,
                "ROA en az %5.",
                "ROA %5 altında veya hesaplanamadı.",
            ),
            (
                ratios.ebitda_margin is not None
                and ratios.ebitda_margin >= Decimal("15"),
                5,
                "FAVÖK marjı en az %15.",
                "FAVÖK marjı %15 altında veya hesaplanamadı.",
            ),
        ),
    )

    annual = snapshot.annual_growth
    growth = _component(
        "Büyüme",
        25,
        (
            (
                annual is not None
                and annual.revenue_growth is not None
                and annual.revenue_growth >= Decimal("10"),
                7,
                "Yıllık hasılat büyümesi en az %10.",
                "Yıllık hasılat büyümesi %10 altında veya eksik.",
            ),
            (
                annual is not None
                and annual.ebitda_growth is not None
                and annual.ebitda_growth >= Decimal("10"),
                7,
                "Yıllık FAVÖK büyümesi en az %10.",
                "Yıllık FAVÖK büyümesi %10 altında veya eksik.",
            ),
            (
                annual is not None
                and annual.net_income_growth is not None
                and annual.net_income_growth >= Decimal("10"),
                7,
                "Yıllık net kâr büyümesi en az %10.",
                "Yıllık net kâr büyümesi %10 altında veya eksik.",
            ),
            (
                annual is not None
                and annual.operating_cash_flow_growth is not None
                and annual.operating_cash_flow_growth > Decimal("0"),
                4,
                "Faaliyet nakit akışı yıllık bazda büyüyor.",
                "Faaliyet nakit akışı yıllık bazda büyümüyor veya eksik.",
            ),
        ),
    )

    leverage = _component(
        "Borçluluk",
        20,
        (
            (
                ratios.debt_to_equity <= Decimal("1"),
                8,
                "Borç/özsermaye oranı 1 veya altında.",
                "Borç/özsermaye oranı 1 üzerinde.",
            ),
            (
                ratios.net_debt_to_ebitda <= Decimal("2"),
                8,
                "Net borç/FAVÖK 2 veya altında.",
                "Net borç/FAVÖK 2 üzerinde.",
            ),
            (
                ratios.net_debt <= Decimal("0"),
                4,
                "Şirket net nakit pozisyonunda.",
                "Şirket net borç pozisyonunda.",
            ),
        ),
    )

    liquidity = _component(
        "Likidite",
        15,
        (
            (
                ratios.current_ratio >= Decimal("1.5"),
                10,
                "Cari oran en az 1,5.",
                "Cari oran 1,5 altında.",
            ),
            (
                latest.cash_and_equivalents > Decimal("0"),
                5,
                "Nakit ve nakit benzerleri pozitif.",
                "Nakit ve nakit benzerleri pozitif değil.",
            ),
        ),
    )

    cash_flow = _component(
        "Nakit akışı",
        15,
        (
            (
                latest.operating_cash_flow > Decimal("0"),
                7,
                "Faaliyet nakit akışı pozitif.",
                "Faaliyet nakit akışı pozitif değil.",
            ),
            (
                ratios.free_cash_flow > Decimal("0"),
                5,
                "Serbest nakit akışı pozitif.",
                "Serbest nakit akışı pozitif değil.",
            ),
            (
                ratios.free_cash_flow_margin >= Decimal("5"),
                3,
                "Serbest nakit akışı marjı en az %5.",
                "Serbest nakit akışı marjı %5 altında.",
            ),
        ),
    )

    total = sum(
        component.score
        for component in (
            profitability,
            growth,
            leverage,
            liquidity,
            cash_flow,
        )
    )

    return FundamentalQualityScore(
        symbol=latest.symbol,
        period_key=latest.period_key,
        total_score=total,
        profitability=profitability,
        growth=growth,
        leverage=leverage,
        liquidity=liquidity,
        cash_flow=cash_flow,
        locked=False,
        explanation=(
            "Temel kalite skoru kârlılık, büyüme, borçluluk, "
            "likidite ve nakit akışı bileşenlerinden üretildi. "
            "Bu skor alım/satım sinyali değildir."
        ),
    )


T = TypeVar("T")


@dataclass(frozen=True)
class OptionalFundamentalFilterResult:
    accepted: tuple[T, ...]
    rejected: tuple[T, ...]
    missing: tuple[T, ...]


def apply_optional_fundamental_filter(
    candidates: Iterable[T],
    *,
    symbol_getter,
    scores: Mapping[str, FundamentalQualityScore],
    enabled: bool,
    minimum_score: int,
) -> OptionalFundamentalFilterResult:
    items = tuple(candidates)

    if not enabled:
        return OptionalFundamentalFilterResult(
            accepted=items,
            rejected=(),
            missing=(),
        )
    if not 0 <= minimum_score <= 100:
        raise ValueError("Minimum temel kalite skoru 0–100 arasında olmalıdır.")

    accepted: list[T] = []
    rejected: list[T] = []
    missing: list[T] = []

    for item in items:
        symbol = str(symbol_getter(item)).removesuffix(".IS").upper()
        score = scores.get(symbol)
        if score is None or score.locked or score.total_score is None:
            missing.append(item)
        elif score.total_score >= minimum_score:
            accepted.append(item)
        else:
            rejected.append(item)

    return OptionalFundamentalFilterResult(
        accepted=tuple(accepted),
        rejected=tuple(rejected),
        missing=tuple(missing),
    )
