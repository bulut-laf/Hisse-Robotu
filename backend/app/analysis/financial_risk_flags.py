from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from ..data.historical_financial_series import HistoricalFinancialPoint, HistoricalFinancialSeries

ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")


@dataclass(frozen=True)
class FinancialRiskFlag:
    code: str
    status: str  # ACTIVE | INACTIVE | NOT_EVALUATED
    severity: str  # INFO | WATCH | WARNING | CRITICAL | UNKNOWN
    reason: str


@dataclass(frozen=True)
class FinancialRiskMetric:
    code: str
    value: Decimal | None
    unit: str


@dataclass(frozen=True)
class FinancialRiskAssessment:
    symbol: str
    risk_score: int | None  # 0 low risk -> 100 high risk
    risk_level: str
    locked: bool
    data_coverage: Decimal
    flags: tuple[FinancialRiskFlag, ...]
    metrics: tuple[FinancialRiskMetric, ...]
    positive_evidence: tuple[str, ...]
    explanation: str
    as_of: datetime | None = None
    engine_version: str = "fin005-v1"


FLAG_ORDER = (
    "NET_DEBT_ACCELERATION",
    "MARGIN_COMPRESSION",
    "NEGATIVE_OPERATING_CASH_FLOW",
    "NEGATIVE_FCF",
    "PROFIT_WITHOUT_CASH",
    "RECEIVABLES_OUTPACE_REVENUE",
    "INVENTORY_BUILDUP",
    "EQUITY_EROSION",
    "SHORT_TERM_DEBT_PRESSURE",
    "INTEREST_COVERAGE_STRESS",
    "DILUTION_RISK",
    "WORKING_CAPITAL_STRESS",
    "AUDITOR_WARNING",
    "GOING_CONCERN_WARNING",
    "RELATED_PARTY_EXPOSURE",
    "CONTINGENT_LIABILITY_RISK",
)

_SEVERITY_POINTS = {"INFO": 0, "WATCH": 10, "WARNING": 25, "CRITICAL": 40, "UNKNOWN": 0}


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


def _resolved(series: HistoricalFinancialSeries, as_of: datetime | None) -> tuple[HistoricalFinancialPoint, ...]:
    return series.available_as_of(as_of).points if as_of is not None else series._resolved_points()


def _latest(points: tuple[HistoricalFinancialPoint, ...], code: str, kind: str, role: str | None = None) -> HistoricalFinancialPoint | None:
    xs = [p for p in points if p.metric_code == code and p.period_kind == kind and (role is None or p.comparison_role == role)]
    return max(xs, key=lambda p: (p.period_end, p.published_at or datetime.min)) if xs else None


def _prior_instant(points: tuple[HistoricalFinancialPoint, ...], current: HistoricalFinancialPoint | None, code: str) -> HistoricalFinancialPoint | None:
    if current is None:
        return None
    xs = [
        p for p in points
        if p.metric_code == code and p.period_kind == "INSTANT" and p.period_end < current.period_end
    ]
    return max(xs, key=lambda p: (p.period_end, p.published_at or datetime.min)) if xs else None


def _prior_year_same_instant(points: tuple[HistoricalFinancialPoint, ...], current: HistoricalFinancialPoint | None, code: str) -> HistoricalFinancialPoint | None:
    if current is None:
        return None
    xs = [
        p for p in points
        if p.metric_code == code
        and p.period_kind == "INSTANT"
        and p.period_end.year == current.period_end.year - 1
        and p.period_end.month == current.period_end.month
        and p.period_end.day == current.period_end.day
    ]
    return max(xs, key=lambda p: p.published_at or datetime.min) if xs else None


def _prior_same_duration(points: tuple[HistoricalFinancialPoint, ...], current: HistoricalFinancialPoint | None, code: str) -> HistoricalFinancialPoint | None:
    if current is None:
        return None
    xs = [
        p for p in points
        if p.metric_code == code
        and p.period_kind == "DURATION"
        and p.comparison_role == "PRIOR_YEAR_SAME_PERIOD"
        and p.period_end.month == current.period_end.month
        and p.period_end.day == current.period_end.day
    ]
    return max(xs, key=lambda p: (p.period_end, p.published_at or datetime.min)) if xs else None


def _v(p: HistoricalFinancialPoint | None) -> Decimal | None:
    return p.value if p is not None else None


def _flag(code: str, status: str, severity: str, reason: str) -> FinancialRiskFlag:
    return FinancialRiskFlag(code=code, status=status, severity=severity, reason=reason)


def calculate_financial_risk_flags(
    series: HistoricalFinancialSeries,
    *,
    as_of: datetime | None = None,
) -> FinancialRiskAssessment:
    pts = _resolved(series, as_of)

    # Current instant balance-sheet facts.
    instant_codes = (
        "CASH_EQUIVALENTS", "CURRENT_ASSETS", "TRADE_RECEIVABLES", "INVENTORIES",
        "SHORT_TERM_BORROWINGS", "CURRENT_PORTION_LONG_TERM_DEBT", "CURRENT_LIABILITIES",
        "LONG_TERM_BORROWINGS", "TOTAL_EQUITY",
    )
    cur_i = {c: _latest(pts, c, "INSTANT", "CURRENT_INSTANT") or _latest(pts, c, "INSTANT") for c in instant_codes}
    prev_i = {c: _prior_instant(pts, cur_i[c], c) for c in instant_codes}
    prev_y_i = {c: _prior_year_same_instant(pts, cur_i[c], c) for c in instant_codes}

    # Current YTD and comparable prior-year durations.
    duration_codes = ("REVENUE", "OPERATING_PROFIT", "NET_INCOME", "OPERATING_CASH_FLOW", "CAPEX", "INTEREST_EXPENSE")
    cur_d = {c: _latest(pts, c, "DURATION", "CURRENT_YTD") for c in duration_codes}
    prev_d = {c: _prior_same_duration(pts, cur_d[c], c) for c in duration_codes}

    cash = _v(cur_i["CASH_EQUIVALENTS"])
    current_assets = _v(cur_i["CURRENT_ASSETS"])
    current_liabilities = _v(cur_i["CURRENT_LIABILITIES"])
    equity = _v(cur_i["TOTAL_EQUITY"])
    st_debt_parts = (_v(cur_i["SHORT_TERM_BORROWINGS"]), _v(cur_i["CURRENT_PORTION_LONG_TERM_DEBT"]))
    lt_debt = _v(cur_i["LONG_TERM_BORROWINGS"])
    st_debt = sum((x for x in st_debt_parts if x is not None), ZERO) if any(x is not None for x in st_debt_parts) else None
    financial_debt = (st_debt + lt_debt) if st_debt is not None and lt_debt is not None else None
    net_debt = financial_debt - cash if financial_debt is not None and cash is not None else None

    prev_cash = _v(prev_i["CASH_EQUIVALENTS"])
    prev_st_parts = (_v(prev_i["SHORT_TERM_BORROWINGS"]), _v(prev_i["CURRENT_PORTION_LONG_TERM_DEBT"]))
    prev_lt_debt = _v(prev_i["LONG_TERM_BORROWINGS"])
    prev_st_debt = sum((x for x in prev_st_parts if x is not None), ZERO) if any(x is not None for x in prev_st_parts) else None
    prev_financial_debt = (prev_st_debt + prev_lt_debt) if prev_st_debt is not None and prev_lt_debt is not None else None
    prev_net_debt = prev_financial_debt - prev_cash if prev_financial_debt is not None and prev_cash is not None else None

    revenue = _v(cur_d["REVENUE"])
    prev_revenue = _v(prev_d["REVENUE"])
    op = _v(cur_d["OPERATING_PROFIT"])
    prev_op = _v(prev_d["OPERATING_PROFIT"])
    net_income = _v(cur_d["NET_INCOME"])
    ocf = _v(cur_d["OPERATING_CASH_FLOW"])
    capex_raw = _v(cur_d["CAPEX"])
    capex = abs(capex_raw) if capex_raw is not None else None
    fcf = ocf - capex if ocf is not None and capex is not None else None

    op_margin = _ratio(op, revenue, pct=True)
    prev_op_margin = _ratio(prev_op, prev_revenue, pct=True)
    margin_delta = _q2(op_margin - prev_op_margin) if op_margin is not None and prev_op_margin is not None else None
    ocf_to_net = _ratio(ocf, net_income)
    st_debt_to_cash = _ratio(st_debt, cash)
    st_debt_to_equity = _ratio(st_debt, equity)
    working_capital = current_assets - current_liabilities if current_assets is not None and current_liabilities is not None else None
    prev_wc = (
        _v(prev_i["CURRENT_ASSETS"]) - _v(prev_i["CURRENT_LIABILITIES"])
        if _v(prev_i["CURRENT_ASSETS"]) is not None and _v(prev_i["CURRENT_LIABILITIES"]) is not None
        else None
    )
    wc_change_pct = _growth(working_capital, prev_wc)
    net_debt_change = net_debt - prev_net_debt if net_debt is not None and prev_net_debt is not None else None
    equity_growth = _growth(equity, _v(prev_i["TOTAL_EQUITY"]))
    revenue_growth = _growth(revenue, prev_revenue)
    receivables_yoy = _growth(_v(cur_i["TRADE_RECEIVABLES"]), _v(prev_y_i["TRADE_RECEIVABLES"]))
    inventory_yoy = _growth(_v(cur_i["INVENTORIES"]), _v(prev_y_i["INVENTORIES"]))

    flags: list[FinancialRiskFlag] = []
    positives: list[str] = []

    # 1 NET_DEBT_ACCELERATION
    if net_debt is None or prev_net_debt is None:
        flags.append(_flag("NET_DEBT_ACCELERATION", "NOT_EVALUATED", "UNKNOWN", "Net borç için karşılaştırılabilir iki bilanço noktası yok."))
    else:
        threshold = max(abs(prev_net_debt) * Decimal("0.25"), (equity or ZERO) * Decimal("0.05"))
        active = net_debt > prev_net_debt and net_debt_change is not None and net_debt_change > threshold
        if active:
            sev = "CRITICAL" if prev_net_debt <= ZERO < net_debt else "WARNING"
            flags.append(_flag("NET_DEBT_ACCELERATION", "ACTIVE", sev, "Net borç önceki bilanço noktasına göre anlamlı biçimde arttı."))
        else:
            flags.append(_flag("NET_DEBT_ACCELERATION", "INACTIVE", "INFO", "Net borçta eşik üstü kötüleşme yok."))
            if net_debt <= ZERO:
                positives.append("NET_CASH")
            if net_debt < prev_net_debt:
                positives.append("NET_DEBT_IMPROVING")

    # 2 MARGIN_COMPRESSION
    if margin_delta is None:
        flags.append(_flag("MARGIN_COMPRESSION", "NOT_EVALUATED", "UNKNOWN", "Karşılaştırılabilir esas faaliyet marjı yok."))
    elif margin_delta <= Decimal("-5"):
        flags.append(_flag("MARGIN_COMPRESSION", "ACTIVE", "WARNING", "Esas faaliyet marjı yıllık karşılaştırmada 5 puandan fazla daraldı."))
    elif margin_delta <= Decimal("-2"):
        flags.append(_flag("MARGIN_COMPRESSION", "ACTIVE", "WATCH", "Esas faaliyet marjında anlamlı daralma var."))
    else:
        flags.append(_flag("MARGIN_COMPRESSION", "INACTIVE", "INFO", "Esas faaliyet marjında eşik üstü daralma yok."))
        if margin_delta > ZERO:
            positives.append("MARGIN_EXPANSION")

    # 3 NEGATIVE_OPERATING_CASH_FLOW
    if ocf is None:
        flags.append(_flag("NEGATIVE_OPERATING_CASH_FLOW", "NOT_EVALUATED", "UNKNOWN", "İşletme nakit akışı yok."))
    elif ocf <= ZERO:
        flags.append(_flag("NEGATIVE_OPERATING_CASH_FLOW", "ACTIVE", "CRITICAL", "İşletme faaliyetlerinden nakit akışı pozitif değil."))
    else:
        flags.append(_flag("NEGATIVE_OPERATING_CASH_FLOW", "INACTIVE", "INFO", "İşletme faaliyetlerinden nakit akışı pozitif."))
        positives.append("POSITIVE_OPERATING_CASH_FLOW")

    # 4 NEGATIVE_FCF
    if fcf is None:
        flags.append(_flag("NEGATIVE_FCF", "NOT_EVALUATED", "UNKNOWN", "FCF için OCF ve CAPEX birlikte bulunamadı."))
    elif fcf < ZERO:
        flags.append(_flag("NEGATIVE_FCF", "ACTIVE", "WARNING", "Basit serbest nakit akışı negatiftir."))
    else:
        flags.append(_flag("NEGATIVE_FCF", "INACTIVE", "INFO", "Basit serbest nakit akışı pozitiftir."))
        positives.append("POSITIVE_FCF")

    # 5 PROFIT_WITHOUT_CASH
    if net_income is None or ocf_to_net is None:
        flags.append(_flag("PROFIT_WITHOUT_CASH", "NOT_EVALUATED", "UNKNOWN", "Kârın nakde dönüşümü için veri yetersiz."))
    elif net_income > ZERO and ocf_to_net < Decimal("0.50"):
        sev = "CRITICAL" if ocf <= ZERO else "WARNING"
        flags.append(_flag("PROFIT_WITHOUT_CASH", "ACTIVE", sev, "Pozitif net kâr yeterli işletme nakit akışıyla desteklenmiyor."))
    else:
        flags.append(_flag("PROFIT_WITHOUT_CASH", "INACTIVE", "INFO", "Kârın nakit desteğinde kritik bozulma yok."))
        if net_income > ZERO and ocf_to_net >= ONE:
            positives.append("STRONG_CASH_CONVERSION")

    # 6 RECEIVABLES_OUTPACE_REVENUE: only same-date YoY balance point is valid.
    if receivables_yoy is None or revenue_growth is None:
        flags.append(_flag("RECEIVABLES_OUTPACE_REVENUE", "NOT_EVALUATED", "UNKNOWN", "Aynı tarihli önceki yıl alacak bakiyesi bulunmadığı için karşılaştırma yapılmadı."))
    elif receivables_yoy > revenue_growth + Decimal("15") and receivables_yoy > Decimal("20"):
        flags.append(_flag("RECEIVABLES_OUTPACE_REVENUE", "ACTIVE", "WARNING", "Ticari alacak büyümesi satış büyümesini anlamlı biçimde aşıyor."))
    else:
        flags.append(_flag("RECEIVABLES_OUTPACE_REVENUE", "INACTIVE", "INFO", "Ticari alacak büyümesi satış büyümesine göre risk eşiğini aşmıyor."))

    # 7 INVENTORY_BUILDUP: also requires same-date YoY balance point.
    if inventory_yoy is None or revenue_growth is None:
        flags.append(_flag("INVENTORY_BUILDUP", "NOT_EVALUATED", "UNKNOWN", "Aynı tarihli önceki yıl stok bakiyesi bulunmadığı için karşılaştırma yapılmadı."))
    elif inventory_yoy > revenue_growth + Decimal("15") and inventory_yoy > Decimal("20"):
        flags.append(_flag("INVENTORY_BUILDUP", "ACTIVE", "WATCH", "Stok büyümesi satış büyümesini belirgin biçimde aşıyor."))
    else:
        flags.append(_flag("INVENTORY_BUILDUP", "INACTIVE", "INFO", "Stok büyümesi satış büyümesine göre risk eşiğini aşmıyor."))

    # 8 EQUITY_EROSION
    if equity_growth is None:
        flags.append(_flag("EQUITY_EROSION", "NOT_EVALUATED", "UNKNOWN", "Özkaynak için karşılaştırılabilir iki bilanço noktası yok."))
    elif equity_growth <= Decimal("-10"):
        flags.append(_flag("EQUITY_EROSION", "ACTIVE", "WARNING", "Özkaynak önceki bilanço noktasına göre %10'dan fazla geriledi."))
    elif equity_growth < ZERO:
        flags.append(_flag("EQUITY_EROSION", "ACTIVE", "WATCH", "Özkaynak önceki bilanço noktasına göre geriledi."))
    else:
        flags.append(_flag("EQUITY_EROSION", "INACTIVE", "INFO", "Özkaynak erozyonu yok."))
        positives.append("EQUITY_GROWTH")

    # 9 SHORT_TERM_DEBT_PRESSURE
    if st_debt is None or (st_debt_to_cash is None and st_debt_to_equity is None):
        flags.append(_flag("SHORT_TERM_DEBT_PRESSURE", "NOT_EVALUATED", "UNKNOWN", "Kısa vadeli finansal borç baskısı için veri yetersiz."))
    elif (st_debt_to_cash is not None and st_debt_to_cash > Decimal("1.5")) or (st_debt_to_equity is not None and st_debt_to_equity > Decimal("0.75")):
        flags.append(_flag("SHORT_TERM_DEBT_PRESSURE", "ACTIVE", "WARNING", "Kısa vadeli finansal borç nakit/özkaynak tamponuna göre yüksek."))
    elif (st_debt_to_cash is not None and st_debt_to_cash > ONE) or (st_debt_to_equity is not None and st_debt_to_equity > Decimal("0.50")):
        flags.append(_flag("SHORT_TERM_DEBT_PRESSURE", "ACTIVE", "WATCH", "Kısa vadeli finansal borç baskısı izlenmelidir."))
    else:
        flags.append(_flag("SHORT_TERM_DEBT_PRESSURE", "INACTIVE", "INFO", "Kısa vadeli finansal borç baskısı düşük."))
        positives.append("SHORT_TERM_DEBT_COVERAGE_STRONG")

    # 10 INTEREST_COVERAGE_STRESS: pure interest expense only; finance expense is not substituted.
    interest_expense = _v(cur_d["INTEREST_EXPENSE"])
    interest_coverage = _ratio(op, abs(interest_expense) if interest_expense is not None else None)
    if interest_coverage is None:
        flags.append(_flag("INTEREST_COVERAGE_STRESS", "NOT_EVALUATED", "UNKNOWN", "Saf faiz gideri canonical veri olarak bulunmadığı için finance expense ikame edilmedi."))
    elif interest_coverage < Decimal("1.5"):
        flags.append(_flag("INTEREST_COVERAGE_STRESS", "ACTIVE", "CRITICAL", "Esas faaliyet kârının faiz giderini karşılama kapasitesi zayıf."))
    elif interest_coverage < Decimal("3"):
        flags.append(_flag("INTEREST_COVERAGE_STRESS", "ACTIVE", "WATCH", "Faiz karşılama oranı izleme eşiğinde."))
    else:
        flags.append(_flag("INTEREST_COVERAGE_STRESS", "INACTIVE", "INFO", "Faiz karşılama oranı sağlıklı."))

    # 11 DILUTION_RISK deferred until FIN-006 share structure exists.
    flags.append(_flag("DILUTION_RISK", "NOT_EVALUATED", "UNKNOWN", "Pay adedi/sermaye hareketleri FIN-006 Ownership & Free Float katmanına bırakıldı."))

    # 12 WORKING_CAPITAL_STRESS
    if working_capital is None:
        flags.append(_flag("WORKING_CAPITAL_STRESS", "NOT_EVALUATED", "UNKNOWN", "Net işletme sermayesi hesaplanamıyor."))
    elif working_capital < ZERO:
        sev = "WARNING" if current_assets and abs(working_capital) / current_assets >= Decimal("0.10") else "WATCH"
        flags.append(_flag("WORKING_CAPITAL_STRESS", "ACTIVE", sev, "Net işletme sermayesi negatiftir."))
    elif prev_wc is not None and wc_change_pct is not None and wc_change_pct <= Decimal("-30"):
        flags.append(_flag("WORKING_CAPITAL_STRESS", "ACTIVE", "WATCH", "Net işletme sermayesinde önceki bilanço noktasına göre belirgin bozulma var."))
    else:
        flags.append(_flag("WORKING_CAPITAL_STRESS", "INACTIVE", "INFO", "Net işletme sermayesinde stres sinyali yok."))
        positives.append("POSITIVE_WORKING_CAPITAL")

    # Note/audit-dependent flags are fail-closed until document-note intelligence exists.
    flags.append(_flag("AUDITOR_WARNING", "NOT_EVALUATED", "UNKNOWN", "Denetçi görüşü sınıflandırma katmanı henüz canonical değildir."))
    flags.append(_flag("GOING_CONCERN_WARNING", "NOT_EVALUATED", "UNKNOWN", "İşletmenin sürekliliği notları için canonical note classifier gerekir."))
    flags.append(_flag("RELATED_PARTY_EXPOSURE", "NOT_EVALUATED", "UNKNOWN", "İlişkili taraf yoğunluğu için not bazlı canonical sınıflandırma gerekir."))
    flags.append(_flag("CONTINGENT_LIABILITY_RISK", "NOT_EVALUATED", "UNKNOWN", "Şarta bağlı yükümlülükler için not bazlı canonical sınıflandırma gerekir."))

    # Preserve contract ordering.
    by_code = {f.code: f for f in flags}
    ordered = tuple(by_code[c] for c in FLAG_ORDER)
    evaluated = [f for f in ordered if f.status != "NOT_EVALUATED"]
    coverage = _q2(Decimal(len(evaluated)) / Decimal(len(FLAG_ORDER)) * HUNDRED)

    # Minimum V1 lock requires the core deterioration spine, not all note/share flags.
    core = {"NET_DEBT_ACCELERATION", "MARGIN_COMPRESSION", "NEGATIVE_OPERATING_CASH_FLOW", "PROFIT_WITHOUT_CASH", "EQUITY_EROSION", "SHORT_TERM_DEBT_PRESSURE", "WORKING_CAPITAL_STRESS"}
    locked = any(by_code[c].status == "NOT_EVALUATED" for c in core)
    if locked:
        risk_score = None
        risk_level = "UNKNOWN"
    else:
        risk_score = min(sum(_SEVERITY_POINTS[f.severity] for f in ordered if f.status == "ACTIVE"), 100)
        risk_level = (
            "LOW" if risk_score <= 14 else
            "LOW_MEDIUM" if risk_score <= 34 else
            "MEDIUM" if risk_score <= 54 else
            "HIGH" if risk_score <= 74 else
            "VERY_HIGH"
        )

    metrics = (
        FinancialRiskMetric("NET_DEBT", net_debt, "currency_scale"),
        FinancialRiskMetric("PREVIOUS_NET_DEBT", prev_net_debt, "currency_scale"),
        FinancialRiskMetric("NET_DEBT_CHANGE", net_debt_change, "currency_scale"),
        FinancialRiskMetric("OPERATING_MARGIN", op_margin, "%"),
        FinancialRiskMetric("PRIOR_OPERATING_MARGIN", prev_op_margin, "%"),
        FinancialRiskMetric("OPERATING_MARGIN_DELTA", margin_delta, "pp"),
        FinancialRiskMetric("OCF_TO_NET_INCOME", ocf_to_net, "x"),
        FinancialRiskMetric("FREE_CASH_FLOW", fcf, "currency_scale"),
        FinancialRiskMetric("SHORT_TERM_DEBT_TO_CASH", st_debt_to_cash, "x"),
        FinancialRiskMetric("SHORT_TERM_DEBT_TO_EQUITY", st_debt_to_equity, "x"),
        FinancialRiskMetric("WORKING_CAPITAL", working_capital, "currency_scale"),
        FinancialRiskMetric("WORKING_CAPITAL_CHANGE", wc_change_pct, "%"),
        FinancialRiskMetric("EQUITY_GROWTH_SINCE_PRIOR_BALANCE", equity_growth, "%"),
        FinancialRiskMetric("REVENUE_GROWTH_YOY", revenue_growth, "%"),
        FinancialRiskMetric("RECEIVABLES_GROWTH_YOY", receivables_yoy, "%"),
        FinancialRiskMetric("INVENTORY_GROWTH_YOY", inventory_yoy, "%"),
        FinancialRiskMetric("INTEREST_COVERAGE", interest_coverage, "x"),
    )

    explanation = (
        "FIN-005 finansal kötüleşme ve risk bayraklarını point-in-time canonical veriden deterministik üretir. "
        "NOT_EVALUATED bir riskin yok olduğu anlamına gelmez; veri/katman eksikliği nedeniyle hüküm verilmediğini gösterir. "
        "Finance expense saf faiz gideri yerine, yıl sonu bilançosu da aynı-tarih YoY bilanço yerine kullanılmaz. "
        "Bu çıktı alım/satım sinyali değildir."
    )
    return FinancialRiskAssessment(
        symbol=series.symbol,
        risk_score=risk_score,
        risk_level=risk_level,
        locked=locked,
        data_coverage=coverage,
        flags=ordered,
        metrics=metrics,
        positive_evidence=tuple(dict.fromkeys(positives)),
        explanation=explanation,
        as_of=as_of,
    )
