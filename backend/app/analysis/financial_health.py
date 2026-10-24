from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from ..data.historical_financial_series import (
    HistoricalFinancialPoint,
    HistoricalFinancialSeries,
)


HUNDRED = Decimal("100")
ONE = Decimal("1")
ZERO = Decimal("0")


@dataclass(frozen=True)
class FinancialHealthMetric:
    code: str
    value: Decimal | None
    unit: str
    source_period_end: str | None
    comparison_value: Decimal | None = None
    comparison_period_end: str | None = None


@dataclass(frozen=True)
class FinancialHealthComponent:
    code: str
    label: str
    score: int | None
    maximum_score: int
    coverage: Decimal
    reasons: tuple[str, ...]
    cautions: tuple[str, ...]


@dataclass(frozen=True)
class FinancialHealthAssessment:
    symbol: str
    score: int | None
    grade: str
    financial_risk: str
    locked: bool
    components: tuple[FinancialHealthComponent, ...]
    metrics: tuple[FinancialHealthMetric, ...]
    positive_evidence: tuple[str, ...]
    cautions: tuple[str, ...]
    data_coverage: Decimal
    explanation: str
    as_of: datetime | None = None
    engine_version: str = "fin003-v1"


@dataclass(frozen=True)
class _Rule:
    available: bool
    earned: int
    maximum: int
    positive: str
    caution: str


def _q2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _ratio(numerator: Decimal | None, denominator: Decimal | None, *, percentage: bool = False) -> Decimal | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    result = numerator / denominator
    if percentage:
        result *= HUNDRED
    return _q2(result)


def _growth(current: Decimal | None, previous: Decimal | None) -> Decimal | None:
    if current is None or previous is None or previous == 0:
        return None
    return _q2((current - previous) / abs(previous) * HUNDRED)


def _score_component(code: str, label: str, maximum_score: int, rules: tuple[_Rule, ...]) -> FinancialHealthComponent:
    available = tuple(rule for rule in rules if rule.available)
    available_max = sum(rule.maximum for rule in available)
    if available_max == 0:
        return FinancialHealthComponent(
            code=code,
            label=label,
            score=None,
            maximum_score=maximum_score,
            coverage=ZERO,
            reasons=(),
            cautions=("Bu bileşen için yeterli canonical veri yok.",),
        )

    raw = sum(rule.earned for rule in available)
    normalized = Decimal(raw) / Decimal(available_max) * Decimal(maximum_score)
    score = int(normalized.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    coverage = _q2(Decimal(available_max) / Decimal(maximum_score) * HUNDRED)
    return FinancialHealthComponent(
        code=code,
        label=label,
        score=min(score, maximum_score),
        maximum_score=maximum_score,
        coverage=min(coverage, HUNDRED),
        reasons=tuple(rule.positive for rule in available if rule.earned > 0),
        cautions=tuple(rule.caution for rule in available if rule.earned == 0),
    )


def _resolved(series: HistoricalFinancialSeries, as_of: datetime | None) -> tuple[HistoricalFinancialPoint, ...]:
    return series.available_as_of(as_of).points if as_of is not None else series._resolved_points()


def _latest_current_instant(points: tuple[HistoricalFinancialPoint, ...], metric: str) -> HistoricalFinancialPoint | None:
    candidates = [
        p for p in points
        if p.metric_code == metric
        and p.period_kind == "INSTANT"
        and p.comparison_role == "CURRENT_INSTANT"
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: (p.period_end, p.published_at or datetime.min))


def _latest_current_ytd(points: tuple[HistoricalFinancialPoint, ...], metric: str) -> HistoricalFinancialPoint | None:
    candidates = [
        p for p in points
        if p.metric_code == metric
        and p.period_kind == "DURATION"
        and p.comparison_role == "CURRENT_YTD"
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: (p.period_end, p.published_at or datetime.min))


def _matching_prior_same_period(
    points: tuple[HistoricalFinancialPoint, ...],
    current: HistoricalFinancialPoint | None,
    metric: str,
) -> HistoricalFinancialPoint | None:
    if current is None or current.period_start is None:
        return None
    candidates = [
        p for p in points
        if p.metric_code == metric
        and p.period_kind == "DURATION"
        and p.comparison_role == "PRIOR_YEAR_SAME_PERIOD"
        and p.period_end.month == current.period_end.month
        and p.period_end.day == current.period_end.day
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: (p.period_end, p.published_at or datetime.min))


def _point_value(point: HistoricalFinancialPoint | None) -> Decimal | None:
    return point.value if point is not None else None


def _metric(
    code: str,
    value: Decimal | None,
    unit: str,
    current: HistoricalFinancialPoint | None,
    comparison_value: Decimal | None = None,
    comparison: HistoricalFinancialPoint | None = None,
) -> FinancialHealthMetric:
    return FinancialHealthMetric(
        code=code,
        value=value,
        unit=unit,
        source_period_end=current.period_end.isoformat() if current else None,
        comparison_value=comparison_value,
        comparison_period_end=comparison.period_end.isoformat() if comparison else None,
    )


def calculate_financial_health(
    series: HistoricalFinancialSeries,
    *,
    as_of: datetime | None = None,
) -> FinancialHealthAssessment:
    points = _resolved(series, as_of)

    cash_p = _latest_current_instant(points, "CASH_EQUIVALENTS")
    current_assets_p = _latest_current_instant(points, "CURRENT_ASSETS")
    total_assets_p = _latest_current_instant(points, "TOTAL_ASSETS")
    current_liabilities_p = _latest_current_instant(points, "CURRENT_LIABILITIES")
    noncurrent_liabilities_p = _latest_current_instant(points, "NONCURRENT_LIABILITIES")
    equity_p = _latest_current_instant(points, "TOTAL_EQUITY")
    st_debt_p = _latest_current_instant(points, "SHORT_TERM_BORROWINGS")
    current_lt_debt_p = _latest_current_instant(points, "CURRENT_PORTION_LT_DEBT")
    lt_debt_p = _latest_current_instant(points, "LONG_TERM_BORROWINGS")

    revenue_p = _latest_current_ytd(points, "REVENUE")
    gross_profit_p = _latest_current_ytd(points, "GROSS_PROFIT")
    operating_profit_p = _latest_current_ytd(points, "OPERATING_PROFIT")
    net_income_p = _latest_current_ytd(points, "NET_INCOME")
    ocf_p = _latest_current_ytd(points, "OPERATING_CASH_FLOW")

    revenue_prior_p = _matching_prior_same_period(points, revenue_p, "REVENUE")
    operating_profit_prior_p = _matching_prior_same_period(points, operating_profit_p, "OPERATING_PROFIT")
    net_income_prior_p = _matching_prior_same_period(points, net_income_p, "NET_INCOME")
    ocf_prior_p = _matching_prior_same_period(points, ocf_p, "OPERATING_CASH_FLOW")

    cash = _point_value(cash_p)
    current_assets = _point_value(current_assets_p)
    total_assets = _point_value(total_assets_p)
    current_liabilities = _point_value(current_liabilities_p)
    noncurrent_liabilities = _point_value(noncurrent_liabilities_p)
    equity = _point_value(equity_p)
    revenue = _point_value(revenue_p)
    gross_profit = _point_value(gross_profit_p)
    operating_profit = _point_value(operating_profit_p)
    net_income = _point_value(net_income_p)
    ocf = _point_value(ocf_p)

    debt_parts = [_point_value(st_debt_p), _point_value(current_lt_debt_p), _point_value(lt_debt_p)]
    financial_debt = sum((v for v in debt_parts if v is not None), ZERO) if any(v is not None for v in debt_parts) else None
    total_liabilities = (
        current_liabilities + noncurrent_liabilities
        if current_liabilities is not None and noncurrent_liabilities is not None
        else None
    )
    net_debt = financial_debt - cash if financial_debt is not None and cash is not None else None

    current_ratio = _ratio(current_assets, current_liabilities)
    cash_ratio = _ratio(cash, current_liabilities)
    equity_ratio = _ratio(equity, total_assets, percentage=True)
    liabilities_to_equity = _ratio(total_liabilities, equity)
    financial_debt_to_equity = _ratio(financial_debt, equity)
    net_debt_to_equity = _ratio(net_debt, equity)

    gross_margin = _ratio(gross_profit, revenue, percentage=True)
    operating_margin = _ratio(operating_profit, revenue, percentage=True)
    net_margin = _ratio(net_income, revenue, percentage=True)
    ocf_to_net_income = _ratio(ocf, net_income)
    ocf_margin = _ratio(ocf, revenue, percentage=True)

    annualization = None
    if revenue_p and revenue_p.period_start:
        days = (revenue_p.period_end - revenue_p.period_start).days + 1
        if days > 0:
            annualization = Decimal("365") / Decimal(days)
    roe_proxy = (
        _q2(net_income / equity * annualization * HUNDRED)
        if net_income is not None and equity not in (None, ZERO) and annualization is not None
        else None
    )
    roa_proxy = (
        _q2(net_income / total_assets * annualization * HUNDRED)
        if net_income is not None and total_assets not in (None, ZERO) and annualization is not None
        else None
    )

    revenue_growth = _growth(revenue, _point_value(revenue_prior_p))
    operating_profit_growth = _growth(operating_profit, _point_value(operating_profit_prior_p))
    net_income_growth = _growth(net_income, _point_value(net_income_prior_p))
    ocf_growth = _growth(ocf, _point_value(ocf_prior_p))
    prior_operating_margin = _ratio(_point_value(operating_profit_prior_p), _point_value(revenue_prior_p), percentage=True)
    operating_margin_delta = (
        _q2(operating_margin - prior_operating_margin)
        if operating_margin is not None and prior_operating_margin is not None
        else None
    )

    liquidity = _score_component(
        "LIQUIDITY",
        "Likidite",
        15,
        (
            _Rule(
                current_ratio is not None,
                8 if current_ratio is not None and current_ratio >= Decimal("1.5") else
                6 if current_ratio is not None and current_ratio >= Decimal("1.2") else
                4 if current_ratio is not None and current_ratio >= ONE else 0,
                8,
                "Cari oran borç ödeme kapasitesini destekliyor.",
                "Cari oran zayıf veya sınırda.",
            ),
            _Rule(
                cash_ratio is not None,
                7 if cash_ratio is not None and cash_ratio >= Decimal("0.50") else
                5 if cash_ratio is not None and cash_ratio >= Decimal("0.30") else
                3 if cash_ratio is not None and cash_ratio >= Decimal("0.15") else 0,
                7,
                "Nakit tamponu kısa vadeli yükümlülüklere karşı güçlü.",
                "Nakit tamponu kısa vadeli yükümlülüklere göre sınırlı.",
            ),
        ),
    )

    balance_sheet = _score_component(
        "BALANCE_SHEET",
        "Bilanço Dayanıklılığı",
        20,
        (
            _Rule(
                equity_ratio is not None,
                8 if equity_ratio is not None and equity_ratio >= Decimal("50") else
                6 if equity_ratio is not None and equity_ratio >= Decimal("35") else
                4 if equity_ratio is not None and equity_ratio >= Decimal("20") else 0,
                8,
                "Özkaynak/aktif oranı bilanço dayanıklılığını destekliyor.",
                "Özkaynak/aktif oranı zayıf.",
            ),
            _Rule(
                financial_debt_to_equity is not None,
                7 if financial_debt_to_equity is not None and financial_debt_to_equity <= Decimal("0.50") else
                5 if financial_debt_to_equity is not None and financial_debt_to_equity <= ONE else
                3 if financial_debt_to_equity is not None and financial_debt_to_equity <= Decimal("1.50") else 0,
                7,
                "Finansal borç/özkaynak seviyesi kontrollü.",
                "Finansal borç/özkaynak seviyesi yüksek.",
            ),
            _Rule(
                net_debt_to_equity is not None,
                5 if net_debt_to_equity is not None and net_debt_to_equity <= ZERO else
                3 if net_debt_to_equity is not None and net_debt_to_equity <= Decimal("0.50") else
                1 if net_debt_to_equity is not None and net_debt_to_equity <= ONE else 0,
                5,
                "Net borç baskısı düşük; net nakit pozisyonu bilanço kalitesini destekliyor." if net_debt is not None and net_debt <= ZERO else "Net borç/özkaynak seviyesi yönetilebilir.",
                "Net borç/özkaynak seviyesi yüksek.",
            ),
        ),
    )

    profitability = _score_component(
        "PROFITABILITY",
        "Kârlılık",
        20,
        (
            _Rule(
                gross_margin is not None,
                4 if gross_margin is not None and gross_margin > ZERO else 0,
                4,
                "Brüt kâr marjı pozitif.",
                "Brüt kâr marjı pozitif değil.",
            ),
            _Rule(
                operating_margin is not None,
                7 if operating_margin is not None and operating_margin >= Decimal("10") else
                5 if operating_margin is not None and operating_margin >= Decimal("5") else
                3 if operating_margin is not None and operating_margin > ZERO else 0,
                7,
                "Esas faaliyet marjı pozitif ve anlamlı.",
                "Esas faaliyet marjı zayıf veya negatif.",
            ),
            _Rule(
                net_margin is not None,
                7 if net_margin is not None and net_margin >= Decimal("10") else
                5 if net_margin is not None and net_margin >= Decimal("5") else
                3 if net_margin is not None and net_margin > ZERO else 0,
                7,
                "Net kâr marjı pozitif ve anlamlı.",
                "Net kâr marjı zayıf veya negatif.",
            ),
            _Rule(
                operating_profit is not None,
                2 if operating_profit is not None and operating_profit > ZERO else 0,
                2,
                "Esas faaliyet kârı pozitif.",
                "Esas faaliyet sonucu pozitif değil.",
            ),
        ),
    )

    cash_quality = _score_component(
        "CASH_QUALITY",
        "Nakit Kalitesi",
        20,
        (
            _Rule(
                ocf is not None,
                6 if ocf is not None and ocf > ZERO else 0,
                6,
                "İşletme faaliyetlerinden nakit akışı pozitif.",
                "İşletme faaliyetlerinden nakit akışı negatif veya sıfır.",
            ),
            _Rule(
                ocf_to_net_income is not None,
                8 if ocf_to_net_income is not None and ocf_to_net_income >= ONE else
                6 if ocf_to_net_income is not None and ocf_to_net_income >= Decimal("0.75") else
                4 if ocf_to_net_income is not None and ocf_to_net_income >= Decimal("0.50") else
                2 if ocf_to_net_income is not None and ocf_to_net_income > ZERO else 0,
                8,
                "Açıklanan kâr işletme nakit akışıyla destekleniyor.",
                "Kârın nakde dönüşümü zayıf.",
            ),
            _Rule(
                ocf_margin is not None,
                6 if ocf_margin is not None and ocf_margin >= Decimal("10") else
                4 if ocf_margin is not None and ocf_margin >= Decimal("5") else
                2 if ocf_margin is not None and ocf_margin > ZERO else 0,
                6,
                "İşletme nakit akışı/hasılat oranı güçlü.",
                "İşletme nakit akışı/hasılat oranı zayıf.",
            ),
        ),
    )

    capital_efficiency = _score_component(
        "CAPITAL_EFFICIENCY",
        "Sermaye Verimliliği",
        15,
        (
            _Rule(
                roe_proxy is not None,
                8 if roe_proxy is not None and roe_proxy >= Decimal("15") else
                6 if roe_proxy is not None and roe_proxy >= Decimal("10") else
                4 if roe_proxy is not None and roe_proxy >= Decimal("5") else
                2 if roe_proxy is not None and roe_proxy > ZERO else 0,
                8,
                "Yıllıklandırılmış ROE göstergesi güçlü.",
                "Yıllıklandırılmış ROE göstergesi zayıf.",
            ),
            _Rule(
                roa_proxy is not None,
                7 if roa_proxy is not None and roa_proxy >= Decimal("8") else
                5 if roa_proxy is not None and roa_proxy >= Decimal("5") else
                3 if roa_proxy is not None and roa_proxy >= Decimal("2") else
                1 if roa_proxy is not None and roa_proxy > ZERO else 0,
                7,
                "Yıllıklandırılmış ROA göstergesi güçlü.",
                "Yıllıklandırılmış ROA göstergesi zayıf.",
            ),
        ),
    )

    stability = _score_component(
        "STABILITY",
        "Finansal İstikrar",
        10,
        (
            _Rule(
                revenue_growth is not None,
                3 if revenue_growth is not None and revenue_growth > ZERO else 0,
                3,
                "Karşılaştırılabilir döneme göre hasılat büyüyor.",
                "Karşılaştırılabilir döneme göre hasılat büyümüyor.",
            ),
            _Rule(
                operating_margin_delta is not None,
                3 if operating_margin_delta is not None and operating_margin_delta >= ZERO else
                2 if operating_margin_delta is not None and operating_margin_delta >= Decimal("-2") else 0,
                3,
                "Esas faaliyet marjı korunuyor veya genişliyor.",
                "Esas faaliyet marjında belirgin daralma var.",
            ),
            _Rule(
                net_income_growth is not None,
                2 if net_income_growth is not None and net_income_growth > ZERO else 0,
                2,
                "Karşılaştırılabilir döneme göre net kâr büyüyor.",
                "Karşılaştırılabilir döneme göre net kâr büyümüyor.",
            ),
            _Rule(
                ocf_growth is not None,
                2 if ocf_growth is not None and ocf_growth > ZERO else 0,
                2,
                "Karşılaştırılabilir döneme göre işletme nakit akışı büyüyor.",
                "Karşılaştırılabilir döneme göre işletme nakit akışı büyümüyor.",
            ),
        ),
    )

    components = (
        liquidity,
        balance_sheet,
        profitability,
        cash_quality,
        capital_efficiency,
        stability,
    )

    total_max = sum(component.maximum_score for component in components)
    covered_max = sum(
        Decimal(component.maximum_score) * component.coverage / HUNDRED
        for component in components
    )
    coverage = _q2(covered_max / Decimal(total_max) * HUNDRED) if total_max else ZERO

    mandatory_codes = {"LIQUIDITY", "BALANCE_SHEET", "PROFITABILITY"}
    mandatory_missing = any(
        component.code in mandatory_codes and component.score is None
        for component in components
    )
    locked = coverage < Decimal("70") or mandatory_missing

    if locked:
        total_score = None
        grade = "DATA_INSUFFICIENT"
        risk = "UNKNOWN"
    else:
        earned = sum(component.score or 0 for component in components)
        available_weight = sum(component.maximum_score for component in components if component.score is not None)
        total_score = int((Decimal(earned) / Decimal(available_weight) * HUNDRED).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        total_score = max(0, min(total_score, 100))
        if total_score >= 90:
            grade = "VERY_STRONG"
            risk = "LOW"
        elif total_score >= 80:
            grade = "STRONG"
            risk = "LOW_MEDIUM"
        elif total_score >= 70:
            grade = "HEALTHY"
            risk = "MEDIUM"
        elif total_score >= 60:
            grade = "WATCH"
            risk = "MEDIUM_HIGH"
        elif total_score >= 50:
            grade = "WEAK"
            risk = "HIGH"
        else:
            grade = "HIGH_RISK"
            risk = "VERY_HIGH"

    positive: list[str] = []
    cautions: list[str] = []
    if net_debt is not None and net_debt <= ZERO:
        positive.append("NET_CASH")
    if ocf_to_net_income is not None and ocf_to_net_income >= ONE:
        positive.append("STRONG_CASH_CONVERSION")
    if equity_ratio is not None and equity_ratio >= Decimal("50"):
        positive.append("EQUITY_STRENGTH")
    if ocf is not None and ocf > ZERO:
        positive.append("POSITIVE_OPERATING_CASH_FLOW")
    if operating_margin_delta is not None and operating_margin_delta > ZERO:
        positive.append("MARGIN_EXPANSION")

    if current_ratio is not None and current_ratio < Decimal("1.5"):
        cautions.append("CURRENT_RATIO_BELOW_1_5")
    if net_income is not None and net_income > ZERO and ocf_to_net_income is not None and ocf_to_net_income < Decimal("0.5"):
        cautions.append("PROFIT_WITH_WEAK_CASH_SUPPORT")
    if operating_margin_delta is not None and operating_margin_delta < Decimal("-2"):
        cautions.append("MARGIN_COMPRESSION")
    if net_debt_to_equity is not None and net_debt_to_equity > ONE:
        cautions.append("NET_DEBT_PRESSURE")

    metrics = (
        _metric("CURRENT_RATIO", current_ratio, "x", current_assets_p),
        _metric("CASH_RATIO", cash_ratio, "x", cash_p),
        _metric("EQUITY_RATIO", equity_ratio, "%", equity_p),
        _metric("LIABILITIES_TO_EQUITY", liabilities_to_equity, "x", equity_p),
        _metric("FINANCIAL_DEBT", financial_debt, series.currency, st_debt_p),
        _metric("NET_DEBT", net_debt, series.currency, cash_p),
        _metric("FINANCIAL_DEBT_TO_EQUITY", financial_debt_to_equity, "x", equity_p),
        _metric("NET_DEBT_TO_EQUITY", net_debt_to_equity, "x", equity_p),
        _metric("GROSS_MARGIN", gross_margin, "%", gross_profit_p),
        _metric("OPERATING_MARGIN", operating_margin, "%", operating_profit_p, prior_operating_margin, operating_profit_prior_p),
        _metric("NET_MARGIN", net_margin, "%", net_income_p),
        _metric("OCF_TO_NET_INCOME", ocf_to_net_income, "x", ocf_p),
        _metric("OCF_MARGIN", ocf_margin, "%", ocf_p),
        _metric("ROE_PROXY_ANNUALIZED", roe_proxy, "%", net_income_p),
        _metric("ROA_PROXY_ANNUALIZED", roa_proxy, "%", net_income_p),
        _metric("REVENUE_GROWTH_COMPARABLE", revenue_growth, "%", revenue_p, _point_value(revenue_prior_p), revenue_prior_p),
        _metric("OPERATING_PROFIT_GROWTH_COMPARABLE", operating_profit_growth, "%", operating_profit_p, _point_value(operating_profit_prior_p), operating_profit_prior_p),
        _metric("NET_INCOME_GROWTH_COMPARABLE", net_income_growth, "%", net_income_p, _point_value(net_income_prior_p), net_income_prior_p),
        _metric("OCF_GROWTH_COMPARABLE", ocf_growth, "%", ocf_p, _point_value(ocf_prior_p), ocf_prior_p),
    )

    explanation = (
        "Financial Health V1; likidite, bilanço dayanıklılığı, kârlılık, nakit kalitesi, "
        "sermaye verimliliği ve karşılaştırılabilir dönem istikrarını deterministic olarak ölçer. "
        "ROE/ROA alanları ara dönem kârının dönem gün sayısına göre yıllıklandırılmış proxy göstergeleridir; "
        "nihai ROIC/ortalama sermaye hesabı değildir. Bu değerlendirme alım/satım sinyali değildir."
    )

    return FinancialHealthAssessment(
        symbol=series.symbol,
        score=total_score,
        grade=grade,
        financial_risk=risk,
        locked=locked,
        components=components,
        metrics=metrics,
        positive_evidence=tuple(positive),
        cautions=tuple(cautions),
        data_coverage=coverage,
        explanation=explanation,
        as_of=as_of,
    )
