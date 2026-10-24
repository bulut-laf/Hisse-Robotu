from __future__ import annotations

from decimal import Decimal

from ..models.fundamental_models import (
    FinancialPeriod,
    FundamentalGrowth,
    FundamentalRatios,
    FundamentalSnapshot,
)


HUNDRED = Decimal("100")


def _safe_ratio(
    numerator: Decimal,
    denominator: Decimal,
    *,
    percentage: bool = False,
) -> Decimal | None:
    if denominator == 0:
        return None
    result = numerator / denominator
    if percentage:
        result *= HUNDRED
    return result.quantize(Decimal("0.01"))


def _growth(
    current: Decimal,
    previous: Decimal,
) -> Decimal | None:
    if previous == 0:
        return None
    return (
        (current - previous) / abs(previous) * HUNDRED
    ).quantize(Decimal("0.01"))


def calculate_ratios(
    period: FinancialPeriod,
) -> FundamentalRatios:
    net_debt = period.total_debt - period.cash_and_equivalents
    free_cash_flow = (
        period.operating_cash_flow - period.capital_expenditure
    )

    return FundamentalRatios(
        symbol=period.symbol,
        period_key=period.period_key,
        gross_margin=_safe_ratio(
            period.gross_profit,
            period.revenue,
            percentage=True,
        ),
        operating_margin=_safe_ratio(
            period.operating_profit,
            period.revenue,
            percentage=True,
        ),
        ebitda_margin=_safe_ratio(
            period.ebitda,
            period.revenue,
            percentage=True,
        ),
        net_margin=_safe_ratio(
            period.net_income,
            period.revenue,
            percentage=True,
        ),
        roe=_safe_ratio(
            period.net_income,
            period.total_equity,
            percentage=True,
        ),
        roa=_safe_ratio(
            period.net_income,
            period.total_assets,
            percentage=True,
        ),
        current_ratio=_safe_ratio(
            period.current_assets,
            period.current_liabilities,
        ),
        debt_to_equity=_safe_ratio(
            period.total_debt,
            period.total_equity,
        ),
        net_debt=net_debt.quantize(Decimal("0.01")),
        net_debt_to_ebitda=_safe_ratio(
            net_debt,
            period.ebitda,
        ),
        free_cash_flow=free_cash_flow.quantize(
            Decimal("0.01")
        ),
        free_cash_flow_margin=_safe_ratio(
            free_cash_flow,
            period.revenue,
            percentage=True,
        ),
    )


def calculate_growth(
    current: FinancialPeriod,
    comparison: FinancialPeriod,
) -> FundamentalGrowth:
    if current.symbol != comparison.symbol:
        raise ValueError(
            "Büyüme karşılaştırması aynı sembol için yapılmalıdır."
        )
    if current.currency != comparison.currency:
        raise ValueError(
            "Büyüme karşılaştırmasında para birimleri aynı olmalıdır."
        )

    return FundamentalGrowth(
        symbol=current.symbol,
        current_period_key=current.period_key,
        comparison_period_key=comparison.period_key,
        revenue_growth=_growth(
            current.revenue,
            comparison.revenue,
        ),
        ebitda_growth=_growth(
            current.ebitda,
            comparison.ebitda,
        ),
        net_income_growth=_growth(
            current.net_income,
            comparison.net_income,
        ),
        equity_growth=_growth(
            current.total_equity,
            comparison.total_equity,
        ),
        operating_cash_flow_growth=_growth(
            current.operating_cash_flow,
            comparison.operating_cash_flow,
        ),
    )


def _quality_flags(
    latest: FinancialPeriod,
    ratios: FundamentalRatios,
) -> tuple[str, ...]:
    flags: list[str] = []

    if latest.net_income < 0:
        flags.append("Dönem net zararla kapandı.")
    if latest.operating_cash_flow < 0:
        flags.append("İşletme faaliyetlerinden nakit akışı negatif.")
    if ratios.free_cash_flow < 0:
        flags.append("Serbest nakit akışı negatif.")
    if (
        ratios.current_ratio is not None
        and ratios.current_ratio < Decimal("1")
    ):
        flags.append("Cari oran 1 seviyesinin altında.")
    if (
        ratios.debt_to_equity is not None
        and ratios.debt_to_equity > Decimal("2")
    ):
        flags.append("Borç/özsermaye oranı 2 seviyesinin üzerinde.")
    if latest.total_equity <= 0:
        flags.append("Özsermaye pozitif değil.")
    if latest.revenue == 0:
        flags.append("Hasılat sıfır; marjlar hesaplanamadı.")

    return tuple(flags)


def build_fundamental_snapshot(
    periods: list[FinancialPeriod],
    *,
    source_metadata: dict[str, str] | None = None,
) -> FundamentalSnapshot:
    if not periods:
        raise ValueError(
            "Temel analiz için en az bir finansal dönem gereklidir."
        )

    symbols = {period.symbol for period in periods}
    currencies = {period.currency for period in periods}
    if len(symbols) != 1:
        raise ValueError(
            "Tek bir temel analiz özeti yalnızca bir sembol içerebilir."
        )
    if len(currencies) != 1:
        raise ValueError(
            "Dönemlerin para birimi aynı olmalıdır."
        )

    ordered = sorted(
        periods,
        key=lambda item: (
            item.period_end,
            item.fiscal_year,
            item.fiscal_quarter,
        ),
        reverse=True,
    )
    latest = ordered[0]

    previous_quarter = next(
        (
            item
            for item in ordered[1:]
            if (
                item.fiscal_year,
                item.fiscal_quarter,
            )
            == _previous_quarter_key(
                latest.fiscal_year,
                latest.fiscal_quarter,
            )
        ),
        None,
    )
    previous_year_same_quarter = next(
        (
            item
            for item in ordered[1:]
            if item.fiscal_year == latest.fiscal_year - 1
            and item.fiscal_quarter == latest.fiscal_quarter
        ),
        None,
    )

    ratios = calculate_ratios(latest)

    return FundamentalSnapshot(
        latest=latest,
        previous_quarter=previous_quarter,
        previous_year_same_quarter=previous_year_same_quarter,
        ratios=ratios,
        quarter_growth=(
            calculate_growth(latest, previous_quarter)
            if previous_quarter is not None
            else None
        ),
        annual_growth=(
            calculate_growth(
                latest,
                previous_year_same_quarter,
            )
            if previous_year_same_quarter is not None
            else None
        ),
        quality_flags=_quality_flags(latest, ratios),
        source_metadata=source_metadata or {},
    )


def _previous_quarter_key(
    fiscal_year: int,
    fiscal_quarter: int,
) -> tuple[int, int]:
    if fiscal_quarter == 1:
        return fiscal_year - 1, 4
    return fiscal_year, fiscal_quarter - 1
