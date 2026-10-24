from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from ..data.kap_financial_xls import import_kap_financial_xls_bytes
from ..data.historical_financial_series import build_historical_financial_series
from .financial_health import calculate_financial_health
from .earnings_cash_quality import calculate_earnings_cash_quality
from .financial_risk_flags import calculate_financial_risk_flags
from .ownership_float import assess_ownership_float
from .market_multiples import calculate_market_multiples
from ..models.valuation_foundation_models import OwnershipSnapshot, MarketSnapshot


def _d(value: str | Decimal | int | float | None) -> Decimal | None:
    if value is None or value == "":
        return None
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _serialize(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime,)):
        return value.isoformat()
    if hasattr(value, "isoformat") and callable(value.isoformat):
        try:
            return value.isoformat()
        except TypeError:
            pass
    if isinstance(value, tuple):
        return [_serialize(x) for x in value]
    if isinstance(value, list):
        return [_serialize(x) for x in value]
    if isinstance(value, dict):
        return {str(k): _serialize(v) for k, v in value.items()}
    if hasattr(value, "__dataclass_fields__"):
        return _serialize(asdict(value))
    return value


def run_financial_intelligence_acceptance(
    xls_path: str | Path,
    *,
    as_of: datetime | None = None,
    price: Decimal | None = None,
    total_shares: Decimal | None = None,
    diluted_shares: Decimal | None = None,
    free_float_ratio: Decimal | None = None,
    effective_free_float_ratio: Decimal | None = None,
    major_shareholder_ratio: Decimal | None = None,
) -> dict[str, Any]:
    path = Path(xls_path)
    report = import_kap_financial_xls_bytes(path.read_bytes(), source_name=path.name)
    series = build_historical_financial_series((report,))
    effective_as_of = as_of or report.identity.published_at

    health = calculate_financial_health(series, as_of=effective_as_of)
    cash_quality = calculate_earnings_cash_quality(series, as_of=effective_as_of)
    risk = calculate_financial_risk_flags(series, as_of=effective_as_of)

    ownership = None
    multiples = None
    valuation_status = "DATA_INSUFFICIENT"

    if total_shares is not None:
        ownership_snapshot = OwnershipSnapshot(
            symbol=report.identity.symbol,
            as_of_date=report.identity.report_date,
            published_at=effective_as_of,
            total_shares=total_shares,
            diluted_shares=diluted_shares,
            free_float_ratio=free_float_ratio,
            effective_free_float_ratio=effective_free_float_ratio,
            major_shareholder_ratio=major_shareholder_ratio,
            source="PRODUCTION_ACCEPTANCE_INPUT",
        )
        ownership = assess_ownership_float(ownership_snapshot, as_of=effective_as_of)

        if price is not None:
            market = MarketSnapshot(
                symbol=report.identity.symbol,
                price_date=report.identity.report_date,
                price=price,
                published_at=effective_as_of,
                source="PRODUCTION_ACCEPTANCE_INPUT",
            )
            multiples = calculate_market_multiples(
                series,
                ownership_snapshot,
                market,
                as_of=effective_as_of,
            )
            valuation_status = "MULTIPLES_AVAILABLE"

    required = {
        "symbol_ok": report.identity.symbol == "TUPRS",
        "canonical_points_present": len(series.points) > 0,
        "health_unlocked": not health.locked and health.score is not None,
        "risk_unlocked": not risk.locked and risk.risk_score is not None,
        "cash_quality_unlocked": not cash_quality.locked and cash_quality.score is not None,
        "read_only": True,
    }
    status = "PASS" if all(required.values()) else "FAIL"

    return _serialize({
        "status": status,
        "mode": "READ_ONLY_PRODUCTION_ACCEPTANCE",
        "identity": report.identity,
        "canonical_fact_count": len(report.facts),
        "historical_point_count": len(series.points),
        "series_warnings": series.warnings,
        "financial_health": health,
        "earnings_cash_quality": cash_quality,
        "financial_risk": risk,
        "ownership": ownership,
        "market_multiples": multiples,
        "valuation_status": valuation_status,
        "acceptance_checks": required,
        "limitations": [
            "Fair value / DCF is not generated without explicit forecast assumptions.",
            "Short-term investability is not generated without market/technical context.",
            "Long-term investability is not generated without business-quality/governance/growth context.",
            "Missing inputs are fail-closed; no values are invented.",
        ],
    })
