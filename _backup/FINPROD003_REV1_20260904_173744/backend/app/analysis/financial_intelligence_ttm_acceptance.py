from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from .ttm_financial_bridge import (
    build_ttm_basis_from_reports,
    import_reports,
    serialize,
)
from ..data.market_ownership_canonical import load_market_ownership_input
from ..models.valuation_foundation_models import OwnershipSnapshot, MarketSnapshot
from .market_multiples import calculate_market_multiples
from ..data.historical_financial_series import build_historical_financial_series


def run_ttm_market_acceptance(
    xls_paths: list[str | Path],
    market_ownership_json: str | Path,
    *,
    price: Decimal | None = None,
    price_date=None,
    as_of: datetime | None = None,
    ebitda_ttm_override: Decimal | None = None,
) -> dict[str, Any]:
    reports = import_reports(xls_paths)
    ttm = build_ttm_basis_from_reports(
        reports,
        as_of=as_of,
        ebitda_ttm_override=ebitda_ttm_override,
    )
    canonical = load_market_ownership_input(market_ownership_json)
    if canonical.symbol != ttm.symbol:
        raise ValueError("market/ownership symbol mismatch")

    series = build_historical_financial_series(reports)
    effective_as_of = ttm.as_of

    own = OwnershipSnapshot(
        symbol=canonical.symbol,
        as_of_date=canonical.as_of_date,
        published_at=canonical.published_at,
        total_shares=canonical.valuation_units,
        free_float_ratio=canonical.free_float_ratio,
        effective_free_float_ratio=canonical.effective_free_float_ratio,
        treasury_shares=canonical.treasury_valuation_units,
        diluted_shares=canonical.diluted_valuation_units,
        major_shareholder_ratio=canonical.controlling_group_ratio,
        privileged_share_flag=canonical.privileged_share_flag,
        source=canonical.ownership_source,
        source_ref=canonical.ownership_source_ref,
    )

    effective_price = price if price is not None else canonical.price_try
    effective_price_date = price_date if price_date is not None else canonical.price_date
    multiples = None
    if effective_price is not None:
        market = MarketSnapshot(
            symbol=canonical.symbol,
            price_date=effective_price_date,
            price=effective_price,
            published_at=canonical.price_published_at or effective_as_of,
            source=canonical.market_source,
        )
        multiples = calculate_market_multiples(
            series,
            own,
            market,
            as_of=effective_as_of,
            ebitda_ttm=ttm.ebitda_ttm,
            fcf_ttm=ttm.free_cash_flow_ttm,
            earnings_ttm=ttm.parent_net_income_ttm or ttm.net_income_ttm,
            revenue_ttm=ttm.revenue_ttm,
        )

    pe_unlocked = multiples is not None and multiples.pe is not None
    ev_ebitda_unlocked = multiples is not None and multiples.ev_ebitda is not None
    p_fcf_unlocked = multiples is not None and multiples.p_fcf is not None

    status = "PASS"
    valuation_status = {
        "pe_unlocked": pe_unlocked,
        "ev_ebitda_unlocked": ev_ebitda_unlocked,
        "p_fcf_unlocked": p_fcf_unlocked,
    }

    return serialize({
        "status": status,
        "mode": "READ_ONLY_PRODUCTION_ACCEPTANCE",
        "symbol": ttm.symbol,
        "ttm_basis": ttm,
        "multiples": multiples,
        "valuation_status": valuation_status,
        "limitations": [
            "EV/EBITDA remains fail-closed unless EBITDA TTM is canonical or explicitly supplied.",
            "TTM uses point-in-time compatible FY + current YTD - prior same-period arithmetic.",
            "No interim figure is blindly annualized.",
            "No AL/SAT, scanner, ranking or portfolio score is mutated.",
        ],
    })
