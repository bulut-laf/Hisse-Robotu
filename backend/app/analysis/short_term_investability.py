from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from ..models.investability_models import InvestabilityResult, MarketContextInput, ScoreComponent

ZERO = Decimal("0")
HUNDRED = Decimal("100")


def _clamp(value: Decimal) -> Decimal:
    return max(ZERO, min(HUNDRED, value))


def _component(code: str, value: Decimal | None, weight: str, reason: str) -> ScoreComponent | None:
    if value is None:
        return None
    return ScoreComponent(code, _clamp(value), Decimal(weight), reason)


def calculate_short_term_investability(
    symbol: str,
    as_of_date: date,
    *,
    financial_health_score: int | None,
    risk_score: int | None,
    financial_momentum: Decimal | None,
    valuation_stretch: Decimal | None,
    market: MarketContextInput,
) -> InvestabilityResult:
    # FIN-013 is read-only evidence. It must not invent missing market context.
    components = tuple(c for c in (
        _component("FINANCIAL_HEALTH", Decimal(financial_health_score) if financial_health_score is not None else None, "0.10", "Finansal sağlık tabanı"),
        _component("FINANCIAL_MOMENTUM", financial_momentum, "0.20", "Son finansal momentum"),
        _component("EARNINGS_SURPRISE", market.earnings_surprise, "0.10", "Sonuç sürprizi / beklenti farkı"),
        _component("TECHNICAL_TREND", market.technical_trend, "0.15", "Teknik trend"),
        _component("RELATIVE_STRENGTH", market.relative_strength, "0.10", "Göreceli güç"),
        _component("VOLUME_LIQUIDITY", market.volume_liquidity, "0.10", "Hacim ve likidite"),
        _component("CATALYST", market.catalyst, "0.10", "KAP / haber katalizörü"),
        _component("VALUATION_STRETCH", valuation_stretch, "0.10", "Değerleme gerilimi"),
        _component("ENTRY_RISK", market.entry_risk, "0.05", "Giriş riski"),
    ) if c is not None)

    if not components:
        return InvestabilityResult(symbol, as_of_date, None, "DATA_INSUFFICIENT", True, (), (), ("Yeterli kanıt yok",), "Kısa dönem skoru üretilemedi.", "LOW", "fin013-v1")

    coverage = sum(c.weight for c in components)
    # Require at least 70% of designed evidence and at least one market/technical component.
    has_market = any(c.code in {"TECHNICAL_TREND", "RELATIVE_STRENGTH", "VOLUME_LIQUIDITY", "CATALYST", "ENTRY_RISK"} for c in components)
    if coverage < Decimal("0.70") or not has_market:
        return InvestabilityResult(symbol, as_of_date, None, "DATA_INSUFFICIENT", True, components, (), ("Kısa dönem için piyasa/teknik kanıt eksik",), "Skor fail-closed kilitlendi.", "LOW", "fin013-v1")

    total_weight = sum(c.weight for c in components)
    raw = sum(c.score * c.weight for c in components) / total_weight
    # Risk score is a penalty rather than another positive metric.
    if risk_score is not None:
        raw -= Decimal(risk_score) * Decimal("0.12")
    score = int(_clamp(raw).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    if score >= 80:
        label = "STRONG_CANDIDATE"
    elif score >= 70:
        label = "POSITIVE"
    elif score >= 60:
        label = "WATCH"
    elif score >= 50:
        label = "NEUTRAL"
    else:
        label = "NOT_ATTRACTIVE"

    strengths = tuple(c.code for c in components if c.score >= 75)
    risks = tuple(c.code for c in components if c.score < 45)
    confidence = "HIGH" if coverage >= Decimal("0.90") else "MEDIUM"
    return InvestabilityResult(symbol, as_of_date, score, label, False, components, strengths, risks, f"Kısa dönem: {score}/100 — {label}. Bu çıktı AL/SAT emri değildir.", confidence, "fin013-v1")
