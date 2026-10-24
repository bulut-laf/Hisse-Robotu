from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

from ..data.kap_financial_xls import import_kap_financial_xls_bytes
from ..data.historical_financial_series import build_historical_financial_series


class TTMBridgeError(ValueError):
    pass


def _D(v: Any) -> Decimal | None:
    if v is None:
        return None
    return v if isinstance(v, Decimal) else Decimal(str(v))


@dataclass(frozen=True)
class TTMBasis:
    symbol: str
    as_of: datetime
    revenue_ttm: Decimal | None
    net_income_ttm: Decimal | None
    parent_net_income_ttm: Decimal | None
    operating_cash_flow_ttm: Decimal | None
    capex_ttm: Decimal | None
    free_cash_flow_ttm: Decimal | None
    ebitda_ttm: Decimal | None
    source_formula: str
    data_flags: tuple[str, ...]
    engine_version: str = "fin-prod-003-v1"


def _iter_points(series, metric_code: str):
    for p in series.points:
        if getattr(p, "metric_code", None) == metric_code:
            yield p


def _select_duration_point(series, metric_code: str, *,
                           period_end: str | None = None,
                           duration_start: str | None = None,
                           comparison_role: str | None = None):
    candidates = list(_iter_points(series, metric_code))
    for p in candidates:
        pe = getattr(p, "period_end", None)
        ds = getattr(p, "duration_start", None)
        cr = getattr(p, "comparison_role", None)
        if period_end is not None and str(pe) != period_end:
            continue
        if duration_start is not None and str(ds) != duration_start:
            continue
        if comparison_role is not None and str(cr) != comparison_role:
            continue
        return p
    return None


def _point_value(p) -> Decimal | None:
    return None if p is None else _D(getattr(p, "value", None))


def _metric(series, code: str, role: str) -> Decimal | None:
    # FIN-002 keeps semantic comparison roles. Prefer those, because they are
    # resistant to quarter/YTD mix-ups.
    return _point_value(_select_duration_point(series, code, comparison_role=role))


def _ttm_from_roles(series, code: str) -> Decimal | None:
    current_ytd = _metric(series, code, "CURRENT_YTD")
    prior_same = _metric(series, code, "PRIOR_YEAR_SAME_PERIOD")
    prior_full = _metric(series, code, "PRIOR_FULL_YEAR")
    if current_ytd is None or prior_same is None or prior_full is None:
        return None
    return prior_full + current_ytd - prior_same


def _ttm_capex(series) -> Decimal | None:
    # CAPEX sign may be stored negative in cash-flow statements. Normalize to
    # a positive cash-outflow magnitude for FCF = CFO - CAPEX.
    v = _ttm_from_roles(series, "CAPEX")
    return None if v is None else abs(v)


def build_ttm_basis_from_reports(
    reports: Iterable[Any],
    *,
    as_of: datetime | None = None,
    ebitda_ttm_override: Decimal | None = None,
) -> TTMBasis:
    reports = tuple(reports)
    if not reports:
        raise TTMBridgeError("at least one report is required")
    symbols = {r.identity.symbol for r in reports}
    if len(symbols) != 1:
        raise TTMBridgeError("all reports must belong to one symbol")
    symbol = next(iter(symbols))

    effective_as_of = as_of or max(
        (r.identity.published_at for r in reports if r.identity.published_at is not None),
        default=datetime.min,
    )
    for r in reports:
        if r.identity.published_at is not None and r.identity.published_at > effective_as_of:
            raise TTMBridgeError("future report leakage detected")

    series = build_historical_financial_series(reports)
    flags: list[str] = []

    revenue_ttm = _ttm_from_roles(series, "REVENUE")
    net_income_ttm = _ttm_from_roles(series, "NET_INCOME")
    parent_net_income_ttm = _ttm_from_roles(series, "PARENT_NET_INCOME")
    ocf_ttm = _ttm_from_roles(series, "OPERATING_CASH_FLOW")
    capex_ttm = _ttm_capex(series)
    fcf_ttm = None if ocf_ttm is None or capex_ttm is None else ocf_ttm - capex_ttm

    if revenue_ttm is None:
        flags.append("TTM_REVENUE_UNAVAILABLE")
    if net_income_ttm is None and parent_net_income_ttm is None:
        flags.append("TTM_EARNINGS_UNAVAILABLE")
    if ocf_ttm is None:
        flags.append("TTM_OCF_UNAVAILABLE")
    if capex_ttm is None:
        flags.append("TTM_CAPEX_UNAVAILABLE")
    if fcf_ttm is None:
        flags.append("TTM_FCF_UNAVAILABLE")

    ebitda_ttm = _D(ebitda_ttm_override)
    if ebitda_ttm is None:
        # Do not synthesize EBITDA from EBIT + depreciation unless every
        # component has been canonically verified across all three TTM legs.
        flags.append("TTM_EBITDA_REQUIRES_CANONICAL_OR_EXPLICIT_OVERRIDE")

    return TTMBasis(
        symbol=symbol,
        as_of=effective_as_of,
        revenue_ttm=revenue_ttm,
        net_income_ttm=net_income_ttm,
        parent_net_income_ttm=parent_net_income_ttm,
        operating_cash_flow_ttm=ocf_ttm,
        capex_ttm=capex_ttm,
        free_cash_flow_ttm=fcf_ttm,
        ebitda_ttm=ebitda_ttm,
        source_formula="TTM = PRIOR_FULL_YEAR + CURRENT_YTD - PRIOR_YEAR_SAME_PERIOD",
        data_flags=tuple(flags),
    )


def import_reports(paths: Iterable[str | Path]):
    reports = []
    for p in paths:
        path = Path(p)
        reports.append(import_kap_financial_xls_bytes(path.read_bytes(), source_name=path.name))
    return tuple(reports)


def serialize(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat") and callable(value.isoformat):
        try:
            return value.isoformat()
        except TypeError:
            pass
    if hasattr(value, "__dataclass_fields__"):
        return serialize(asdict(value))
    if isinstance(value, dict):
        return {str(k): serialize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize(v) for v in value]
    return value
