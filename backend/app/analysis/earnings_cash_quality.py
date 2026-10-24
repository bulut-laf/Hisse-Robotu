from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from ..data.historical_financial_series import HistoricalFinancialPoint, HistoricalFinancialSeries

ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")


@dataclass(frozen=True)
class EarningsCashMetric:
    code: str
    value: Decimal | None
    unit: str
    current_period_end: str | None = None
    comparison_value: Decimal | None = None
    comparison_period_end: str | None = None


@dataclass(frozen=True)
class EarningsCashQualityAssessment:
    symbol: str
    score: int | None
    grade: str
    locked: bool
    data_coverage: Decimal
    earnings_quality: str
    cash_quality: str
    normalized_earnings_status: str
    metrics: tuple[EarningsCashMetric, ...]
    positive_evidence: tuple[str, ...]
    cautions: tuple[str, ...]
    explanation: str
    as_of: datetime | None = None
    engine_version: str = "fin004-v1"


def _q2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _ratio(a: Decimal | None, b: Decimal | None, *, pct: bool = False) -> Decimal | None:
    if a is None or b in (None, ZERO):
        return None
    v = a / b
    if pct:
        v *= HUNDRED
    return _q2(v)


def _growth(cur: Decimal | None, prev: Decimal | None) -> Decimal | None:
    if cur is None or prev in (None, ZERO):
        return None
    return _q2((cur - prev) / abs(prev) * HUNDRED)


def _points(series: HistoricalFinancialSeries, as_of: datetime | None) -> tuple[HistoricalFinancialPoint, ...]:
    return series.available_as_of(as_of).points if as_of is not None else series._resolved_points()


def _latest_ytd(points: tuple[HistoricalFinancialPoint, ...], code: str) -> HistoricalFinancialPoint | None:
    xs = [p for p in points if p.metric_code == code and p.period_kind == "DURATION" and p.comparison_role == "CURRENT_YTD"]
    return max(xs, key=lambda p: (p.period_end, p.published_at or datetime.min)) if xs else None


def _prior_same(points: tuple[HistoricalFinancialPoint, ...], cur: HistoricalFinancialPoint | None, code: str) -> HistoricalFinancialPoint | None:
    if cur is None:
        return None
    xs = [p for p in points if p.metric_code == code and p.period_kind == "DURATION" and p.comparison_role == "PRIOR_YEAR_SAME_PERIOD" and p.period_end.month == cur.period_end.month and p.period_end.day == cur.period_end.day]
    return max(xs, key=lambda p: (p.period_end, p.published_at or datetime.min)) if xs else None


def _v(p: HistoricalFinancialPoint | None) -> Decimal | None:
    return p.value if p else None


def _metric(code: str, value: Decimal | None, unit: str, cur: HistoricalFinancialPoint | None, comp: Decimal | None = None, prior: HistoricalFinancialPoint | None = None) -> EarningsCashMetric:
    return EarningsCashMetric(code, value, unit, cur.period_end.isoformat() if cur else None, comp, prior.period_end.isoformat() if prior else None)


def calculate_earnings_cash_quality(series: HistoricalFinancialSeries, *, as_of: datetime | None = None) -> EarningsCashQualityAssessment:
    pts = _points(series, as_of)

    codes = [
        "REVENUE", "GROSS_PROFIT", "OPERATING_PROFIT", "PRETAX_PROFIT", "NET_INCOME",
        "OPERATING_CASH_FLOW", "CAPEX", "FINANCE_INCOME", "FINANCE_EXPENSE",
        "OTHER_OPERATING_INCOME", "OTHER_OPERATING_EXPENSE", "INVESTMENT_INCOME",
        "INVESTMENT_EXPENSE", "EQUITY_METHOD_SHARE", "MONETARY_GAIN_LOSS", "TAX_EXPENSE",
        "DEPRECIATION_AMORTIZATION", "INTEREST_PAID", "INTEREST_RECEIVED"
    ]
    cur = {c: _latest_ytd(pts, c) for c in codes}
    prior = {c: _prior_same(pts, cur[c], c) for c in codes}
    val = {c: _v(cur[c]) for c in codes}
    pval = {c: _v(prior[c]) for c in codes}

    revenue = val["REVENUE"]
    op = val["OPERATING_PROFIT"]
    pretax = val["PRETAX_PROFIT"]
    net = val["NET_INCOME"]
    ocf = val["OPERATING_CASH_FLOW"]
    capex_raw = val["CAPEX"]
    capex = abs(capex_raw) if capex_raw is not None else None
    fcf = ocf - capex if ocf is not None and capex is not None else None

    ocf_to_net = _ratio(ocf, net)
    fcf_to_net = _ratio(fcf, net)
    accrual_gap = net - ocf if net is not None and ocf is not None else None
    accrual_ratio = _ratio(accrual_gap, abs(net) if net is not None else None, pct=True)
    op_margin = _ratio(op, revenue, pct=True)
    net_margin = _ratio(net, revenue, pct=True)
    fcf_margin = _ratio(fcf, revenue, pct=True)
    op_to_pretax = _ratio(op, pretax)

    revenue_growth = _growth(revenue, pval["REVENUE"])
    op_growth = _growth(op, pval["OPERATING_PROFIT"])
    net_growth = _growth(net, pval["NET_INCOME"])
    ocf_growth = _growth(ocf, pval["OPERATING_CASH_FLOW"])

    noncore_items = [val[c] for c in ("INVESTMENT_INCOME", "INVESTMENT_EXPENSE", "EQUITY_METHOD_SHARE", "MONETARY_GAIN_LOSS") if val[c] is not None]
    noncore_abs = sum((abs(x) for x in noncore_items), ZERO) if noncore_items else None
    noncore_to_pretax = _ratio(noncore_abs, abs(pretax) if pretax is not None else None, pct=True)

    mandatory = [revenue, op, net, ocf]
    optional = [pretax, capex, val["FINANCE_EXPENSE"], val["MONETARY_GAIN_LOSS"], val["TAX_EXPENSE"]]
    coverage = _q2(Decimal(sum(x is not None for x in mandatory) * 70 + sum(x is not None for x in optional) * 6) / Decimal("100") * HUNDRED)
    coverage = min(coverage, HUNDRED)
    locked = any(x is None for x in mandatory) or coverage < Decimal("70")

    positives: list[str] = []
    cautions: list[str] = []
    score = 0

    if not locked:
        # Earnings quality: 50 points
        if op is not None and op > ZERO:
            score += 12; positives.append("POSITIVE_OPERATING_PROFIT")
        else:
            cautions.append("NEGATIVE_OPERATING_RESULT")
        if op_to_pretax is not None and op_to_pretax >= Decimal("0.70"):
            score += 12; positives.append("PRETAX_PROFIT_OPERATING_SUPPORTED")
        elif op_to_pretax is not None and op_to_pretax >= Decimal("0.40"):
            score += 7
        else:
            cautions.append("PRETAX_PROFIT_NONCORE_DEPENDENCE")
        if noncore_to_pretax is not None and noncore_to_pretax <= Decimal("20"):
            score += 10; positives.append("NONCORE_DEPENDENCE_LOW")
        elif noncore_to_pretax is not None and noncore_to_pretax <= Decimal("40"):
            score += 6
        elif noncore_to_pretax is not None:
            cautions.append("NONCORE_ITEMS_MATERIAL")
        if net_growth is not None and net_growth > ZERO and op_growth is not None and op_growth > ZERO:
            score += 8; positives.append("EARNINGS_GROWTH_OPERATING_SUPPORTED")
        elif net_growth is not None and net_growth > ZERO:
            score += 4; cautions.append("NET_INCOME_GROWTH_NOT_FULLY_OPERATING_SUPPORTED")
        if op_margin is not None and op_margin > ZERO:
            score += 8

        # Cash quality: 50 points
        if ocf is not None and ocf > ZERO:
            score += 12; positives.append("POSITIVE_OPERATING_CASH_FLOW")
        else:
            cautions.append("NEGATIVE_OPERATING_CASH_FLOW")
        if ocf_to_net is not None and ocf_to_net >= ONE:
            score += 16; positives.append("STRONG_CASH_CONVERSION")
        elif ocf_to_net is not None and ocf_to_net >= Decimal("0.75"):
            score += 12
        elif ocf_to_net is not None and ocf_to_net >= Decimal("0.50"):
            score += 7; cautions.append("CASH_CONVERSION_WATCH")
        else:
            cautions.append("PROFIT_WITHOUT_CASH")
        if fcf is not None and fcf > ZERO:
            score += 12; positives.append("POSITIVE_FCF")
        elif fcf is not None:
            cautions.append("NEGATIVE_FCF")
        if accrual_ratio is not None and accrual_ratio <= ZERO:
            score += 5; positives.append("LOW_ACCRUAL_RISK")
        elif accrual_ratio is not None and accrual_ratio <= Decimal("25"):
            score += 3
        elif accrual_ratio is not None:
            cautions.append("HIGH_ACCRUAL_GAP")
        if ocf_growth is not None and ocf_growth > ZERO:
            score += 5; positives.append("CASH_FLOW_GROWTH")

        score = min(score, 100)

    if locked:
        grade = "DATA_INSUFFICIENT"
        eq = "UNKNOWN"
        cq = "UNKNOWN"
        score_out = None
    else:
        score_out = score
        grade = "VERY_HIGH" if score >= 85 else "HIGH" if score >= 70 else "MEDIUM" if score >= 55 else "LOW" if score >= 40 else "VERY_LOW"
        eq = "HIGH" if score >= 70 and "PRETAX_PROFIT_NONCORE_DEPENDENCE" not in cautions else "MEDIUM" if score >= 50 else "LOW"
        cq = "HIGH" if ocf_to_net is not None and ocf_to_net >= Decimal("0.75") and (fcf is None or fcf > ZERO) else "MEDIUM" if ocf is not None and ocf > ZERO else "LOW"

    # True normalized earnings require explicit one-off classification. Do not fabricate it.
    normalized_status = "NOT_AVAILABLE_WITHOUT_ONE_OFF_CLASSIFICATION"

    metrics = (
        _metric("OPERATING_MARGIN", op_margin, "%", cur["OPERATING_PROFIT"]),
        _metric("NET_MARGIN", net_margin, "%", cur["NET_INCOME"]),
        _metric("OCF_TO_NET_INCOME", ocf_to_net, "x", cur["OPERATING_CASH_FLOW"]),
        _metric("FREE_CASH_FLOW", fcf, "currency_scale", cur["OPERATING_CASH_FLOW"]),
        _metric("FCF_TO_NET_INCOME", fcf_to_net, "x", cur["OPERATING_CASH_FLOW"]),
        _metric("FCF_MARGIN", fcf_margin, "%", cur["OPERATING_CASH_FLOW"]),
        _metric("ACCRUAL_GAP", accrual_gap, "currency_scale", cur["NET_INCOME"]),
        _metric("ACCRUAL_RATIO", accrual_ratio, "%", cur["NET_INCOME"]),
        _metric("OPERATING_TO_PRETAX", op_to_pretax, "x", cur["OPERATING_PROFIT"]),
        _metric("NONCORE_TO_PRETAX", noncore_to_pretax, "%", cur["PRETAX_PROFIT"]),
        _metric("REVENUE_GROWTH_YOY", revenue_growth, "%", cur["REVENUE"], pval["REVENUE"], prior["REVENUE"]),
        _metric("OPERATING_PROFIT_GROWTH_YOY", op_growth, "%", cur["OPERATING_PROFIT"], pval["OPERATING_PROFIT"], prior["OPERATING_PROFIT"]),
        _metric("NET_INCOME_GROWTH_YOY", net_growth, "%", cur["NET_INCOME"], pval["NET_INCOME"], prior["NET_INCOME"]),
        _metric("OCF_GROWTH_YOY", ocf_growth, "%", cur["OPERATING_CASH_FLOW"], pval["OPERATING_CASH_FLOW"], prior["OPERATING_CASH_FLOW"]),
    )

    explanation = (
        "Bu değerlendirme kârın esas faaliyet ve nakit akışıyla desteklenme kalitesini ölçer; "
        "normalize kâr yalnız açık tek-seferlik kalem sınıflandırması varsa üretilebilir. "
        "Bu çıktı alım/satım sinyali değildir."
    )
    return EarningsCashQualityAssessment(
        symbol=series.symbol,
        score=score_out,
        grade=grade,
        locked=locked,
        data_coverage=coverage,
        earnings_quality=eq,
        cash_quality=cq,
        normalized_earnings_status=normalized_status,
        metrics=metrics,
        positive_evidence=tuple(dict.fromkeys(positives)),
        cautions=tuple(dict.fromkeys(cautions)),
        explanation=explanation,
        as_of=as_of,
    )
