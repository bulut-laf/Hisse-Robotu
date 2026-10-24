from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from ..models.investability_models import InvestabilityResult, LongTermContextInput, ScoreComponent

ZERO = Decimal("0")
HUNDRED = Decimal("100")


def _clamp(value: Decimal) -> Decimal:
    return max(ZERO, min(HUNDRED, value))


def _component(code: str, value: Decimal | None, weight: str, reason: str) -> ScoreComponent | None:
    if value is None:
        return None
    return ScoreComponent(code, _clamp(value), Decimal(weight), reason)


def calculate_long_term_investability(
    symbol: str,
    as_of_date: date,
    *,
    financial_health_score: int | None,
    financial_risk_score: int | None,
    cash_quality_score: Decimal | None,
    capital_efficiency_score: Decimal | None,
    valuation_score: Decimal | None,
    margin_of_safety_score: Decimal | None,
    context: LongTermContextInput,
) -> InvestabilityResult:
    components = tuple(c for c in (
        _component("BUSINESS_QUALITY", context.business_quality, "0.15", "İş modeli / kalite sürekliliği"),
        _component("FINANCIAL_HEALTH", Decimal(financial_health_score) if financial_health_score is not None else None, "0.15", "Finansal sağlık"),
        _component("CASH_QUALITY", cash_quality_score, "0.12", "Nakit üretim kalitesi"),
        _component("CAPITAL_EFFICIENCY", capital_efficiency_score, "0.12", "ROIC/sermaye verimliliği"),
        _component("GROWTH_DURABILITY", context.growth_durability, "0.12", "Büyüme sürekliliği"),
        _component("GOVERNANCE", context.governance, "0.08", "Yönetişim"),
        _component("VALUATION", valuation_score, "0.12", "Değerleme"),
        _component("MARGIN_OF_SAFETY", margin_of_safety_score, "0.09", "Güvenlik marjı"),
        _component("SECTOR_RESILIENCE", None if context.sector_risk is None else HUNDRED - _clamp(context.sector_risk), "0.05", "Sektör riski"),
    ) if c is not None)

    coverage = sum(c.weight for c in components)
    if coverage < Decimal("0.70"):
        return InvestabilityResult(symbol, as_of_date, None, "DATA_INSUFFICIENT", True, components, (), ("Uzun dönem için temel kanıt eksik",), "Skor fail-closed kilitlendi.", "LOW", "fin014-v1")

    total_weight = sum(c.weight for c in components)
    raw = sum(c.score * c.weight for c in components) / total_weight
    if financial_risk_score is not None:
        raw -= Decimal(financial_risk_score) * Decimal("0.10")
    score = int(_clamp(raw).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    if score >= 80:
        label = "STRONG_LONG_TERM_CANDIDATE"
    elif score >= 70:
        label = "ATTRACTIVE"
    elif score >= 60:
        label = "WATCH_PRICE_WAIT"
    elif score >= 50:
        label = "NEUTRAL"
    else:
        label = "RISKY"

    strengths = tuple(c.code for c in components if c.score >= 75)
    risks = tuple(c.code for c in components if c.score < 45)
    confidence = "HIGH" if coverage >= Decimal("0.90") else "MEDIUM"
    return InvestabilityResult(symbol, as_of_date, score, label, False, components, strengths, risks, f"Uzun dönem: {score}/100 — {label}. Şirket kalitesi ve fiyat uygunluğu ayrı değerlendirilmiştir.", confidence, "fin014-v1")
