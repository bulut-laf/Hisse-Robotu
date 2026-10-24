from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from ..data.kap_financial_xls import import_kap_financial_xls_bytes
from ..data.historical_financial_series import build_historical_financial_series
from ..data.market_ownership_canonical import CanonicalMarketOwnershipInput
from ..models.valuation_foundation_models import OwnershipSnapshot, MarketSnapshot
from .ownership_float import assess_ownership_float
from .market_multiples import calculate_market_multiples


def _ser(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat") and callable(value.isoformat):
        try:
            return value.isoformat()
        except TypeError:
            pass
    if isinstance(value, dict):
        return {str(k): _ser(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_ser(v) for v in value]
    if hasattr(value, "__dataclass_fields__"):
        return _ser(asdict(value))
    return value


def run_market_ownership_acceptance(
    xls_paths: list[str | Path],
    canonical: CanonicalMarketOwnershipInput,
    *,
    as_of: datetime | None = None,
    ebitda_ttm: Decimal | None = None,
    fcf_ttm: Decimal | None = None,
) -> dict[str, Any]:
    canonical.validate()
    reports = []
    for path in xls_paths:
        p = Path(path)
        reports.append(import_kap_financial_xls_bytes(p.read_bytes(), source_name=p.name))
    if not reports:
        raise ValueError("at least one KAP XLS is required")

    symbol = reports[0].identity.symbol
    if any(r.identity.symbol != symbol for r in reports):
        raise ValueError("all financial reports must belong to same symbol")
    if canonical.symbol != symbol:
        raise ValueError("canonical market/ownership symbol mismatch")

    series = build_historical_financial_series(tuple(reports))
    effective_as_of = as_of or max(
        (r.identity.published_at for r in reports if r.identity.published_at is not None),
        default=datetime.combine(canonical.as_of_date, datetime.min.time()),
    )

    if canonical.published_at is not None and canonical.published_at > effective_as_of:
        raise ValueError("ownership snapshot was not public at requested as_of")
    if canonical.price_published_at is not None and canonical.price_published_at > effective_as_of:
        raise ValueError("market snapshot was not public at requested as_of")

    own = OwnershipSnapshot(
        symbol=symbol,
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
    ownership_assessment = assess_ownership_float(own, as_of=effective_as_of)

    multiples = None
    if canonical.price_try is not None:
        market = MarketSnapshot(
            symbol=symbol,
            price_date=canonical.price_date,
            price=canonical.price_try,
            published_at=canonical.price_published_at,
            source=canonical.market_source,
        )
        multiples = calculate_market_multiples(
            series, own, market,
            as_of=effective_as_of,
            ebitda_ttm=ebitda_ttm,
            fcf_ttm=fcf_ttm,
        )

    pb_available = multiples is not None and multiples.pb is not None
    pe_available = multiples is not None and multiples.pe is not None

    if multiples is None:
        valuation_status = "MARKET_PRICE_REQUIRED"
    elif pb_available and pe_available:
        valuation_status = "PE_PB_UNLOCKED"
    elif pb_available:
        valuation_status = "PB_UNLOCKED_PE_NEEDS_TTM_EARNINGS"
    else:
        valuation_status = "MULTIPLES_PARTIAL"

    parent_equity = None
    eps_ttm = None
    book_value_per_unit = None
    if multiples is not None:
        parent_equity = multiples.equity_value_basis
        if parent_equity is not None:
            book_value_per_unit = parent_equity / canonical.canonical_valuation_units
        if multiples.earnings_basis is not None:
            eps_ttm = multiples.earnings_basis / canonical.canonical_valuation_units

    return _ser({
        "status": "PASS",
        "mode": "READ_ONLY_PRODUCTION_ACCEPTANCE",
        "symbol": symbol,
        "as_of": effective_as_of,
        "input_convention": {
            "issued_capital_try": canonical.issued_capital_try,
            "quote_nominal_unit_try": canonical.quote_nominal_unit_try,
            "valuation_units": canonical.valuation_units,
            "legal_share_nominal_try": canonical.legal_share_nominal_try,
            "legal_share_piece_count": canonical.legal_share_piece_count,
            "note": "Market-cap uses BIST quote lot-equivalent valuation units, not raw legal share-piece count when nominal share value differs from TRY 1.",
        },
        "ownership": ownership_assessment,
        "market": {
            "price_try": canonical.price_try,
            "price_date": canonical.price_date,
            "market_cap_try": canonical.market_cap_try,
            "free_float_market_cap_try": canonical.free_float_market_cap_try,
            "free_float_ratio": canonical.free_float_ratio,
            "effective_free_float_ratio": canonical.effective_free_float_ratio,
            "controlling_group_ratio": canonical.controlling_group_ratio,
        },
        "multiples": multiples,
        "derived_per_unit": {
            "book_value_per_valuation_unit_try": book_value_per_unit,
            "ttm_eps_per_valuation_unit_try": eps_ttm,
        },
        "valuation_status": valuation_status,
        "data_flags": [] if multiples is None else list(multiples.data_flags),
        "limitations": [
            "P/E remains unavailable until a reliable TTM earnings basis exists; interim profit is not blindly annualized.",
            "EV/EBITDA remains unavailable until reliable TTM EBITDA is supplied or canonically derived.",
            "This layer does not generate a DCF/fair value without forecast assumptions.",
            "No AL/SAT, ranking, scanner or portfolio score is mutated.",
        ],
    })
