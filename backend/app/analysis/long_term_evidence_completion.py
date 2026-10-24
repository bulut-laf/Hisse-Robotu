from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any
import json


class LongTermEvidenceCompletionError(ValueError):
    pass


def _D(v: Any) -> Decimal | None:
    if v is None:
        return None
    return v if isinstance(v, Decimal) else Decimal(str(v))


def _clamp100(v: Decimal) -> Decimal:
    return max(Decimal("0"), min(Decimal("100"), v))


def _metric_map(financial_acceptance: dict[str, Any]) -> dict[str, Decimal]:
    """
    Read FIN-004 canonical metrics from the real acceptance payload.
    Supports both direct earnings_cash_quality and nested financial_intelligence shapes.
    """
    eq = (
        financial_acceptance.get("earnings_cash_quality")
        or financial_acceptance.get("earnings_quality")
        or {}
    )
    metrics = eq.get("metrics") or ()
    out: dict[str, Decimal] = {}
    for item in metrics:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "").upper()
        value = _D(item.get("value"))
        if code and value is not None:
            out[code] = value
    return out


def growth_evidence_score(financial_acceptance: dict[str, Any]) -> tuple[Decimal | None, tuple[str, ...]]:
    """
    Conservative single-period growth evidence adapter.

    It deliberately does NOT claim multi-year durability from one YoY observation.
    Four canonical YoY metrics are used:
      REVENUE_GROWTH_YOY
      OPERATING_PROFIT_GROWTH_YOY
      NET_INCOME_GROWTH_YOY
      OCF_GROWTH_YOY

    4/4 positive -> 70 max, not 100.
    3/4 positive -> 60
    2/4 positive -> 50
    1/4 positive -> 35
    0/4 positive -> 20
    Missing <3 metrics -> None (fail closed).
    """
    m = _metric_map(financial_acceptance)
    codes = (
        "REVENUE_GROWTH_YOY",
        "OPERATING_PROFIT_GROWTH_YOY",
        "NET_INCOME_GROWTH_YOY",
        "OCF_GROWTH_YOY",
    )
    vals = [(c, m.get(c)) for c in codes]
    available = [(c, v) for c, v in vals if v is not None]
    if len(available) < 3:
        return None, ("GROWTH_EVIDENCE_INSUFFICIENT_LT3",)

    positive = sum(1 for _, v in available if v > 0)
    negative = sum(1 for _, v in available if v < 0)

    if positive == len(available):
        score = Decimal("70")
    elif positive >= 3:
        score = Decimal("60")
    elif positive == 2:
        score = Decimal("50")
    elif positive == 1:
        score = Decimal("35")
    else:
        score = Decimal("20")

    flags = [
        f"GROWTH_METRICS_AVAILABLE_{len(available)}",
        f"GROWTH_METRICS_POSITIVE_{positive}",
        f"GROWTH_METRICS_NEGATIVE_{negative}",
        "SINGLE_PERIOD_GROWTH_EVIDENCE_CAPPED_AT_70",
        "NOT_MULTI_YEAR_DURABILITY_PROOF",
    ]
    return _clamp100(score), tuple(flags)


def financial_momentum_score(financial_acceptance: dict[str, Any]) -> Decimal | None:
    """
    Short-term financial momentum adapter from the same canonical YoY metrics.
    This is not technical momentum.
    """
    m = _metric_map(financial_acceptance)
    codes = (
        "REVENUE_GROWTH_YOY",
        "OPERATING_PROFIT_GROWTH_YOY",
        "NET_INCOME_GROWTH_YOY",
        "OCF_GROWTH_YOY",
    )
    vals = [m.get(c) for c in codes if m.get(c) is not None]
    if len(vals) < 3:
        return None
    positives = sum(1 for v in vals if v > 0)
    negatives = sum(1 for v in vals if v < 0)
    return _clamp100(Decimal("50") + Decimal("12.5") * Decimal(positives - negatives))


def complete_evidence(
    *,
    financial_acceptance: dict[str, Any],
    existing_evidence: dict[str, Any],
) -> dict[str, Any]:
    growth_score, growth_flags = growth_evidence_score(financial_acceptance)
    fin_momentum = financial_momentum_score(financial_acceptance)

    out = dict(existing_evidence)
    lt = dict(out.get("long_term_context") or {})
    lt["growth_durability"] = str(growth_score) if growth_score is not None else None
    out["long_term_context"] = lt
    out["financial_momentum"] = str(fin_momentum) if fin_momentum is not None else out.get("financial_momentum")

    flags = list(out.get("flags") or [])
    flags = [x for x in flags if x != "GROWTH_DURABILITY_NOT_SYNTHESIZED"]
    flags.extend(growth_flags)

    # Explicitly preserve unresolved evidence instead of manufacturing unlock.
    if growth_score is not None:
        flags.append("LONG_TERM_CANONICAL_COVERAGE_EXPECTED_0_68")
        flags.append("LONG_TERM_STILL_BELOW_0_70_THRESHOLD")
    flags.append("BUSINESS_QUALITY_REMAINS_UNWIRED")
    flags.append("CAPITAL_EFFICIENCY_REMAINS_UNWIRED")
    flags.append("SECTOR_RISK_REMAINS_UNWIRED")

    out["flags"] = list(dict.fromkeys(flags))
    out["engine_version"] = "fin-prod-008-v1"
    out["coverage_assessment"] = {
        "before": "0.56",
        "growth_durability_weight": "0.12" if growth_score is not None else "0.00",
        "after_expected": "0.68" if growth_score is not None else "0.56",
        "unlock_threshold": "0.70",
        "expected_locked": True,
        "reason": (
            "Canonical single-period growth evidence adds 0.12, but no proven "
            "business-quality/capital-efficiency/sector-risk adapter is available yet."
        ),
    }
    return out


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_json(path: str | Path, payload: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
