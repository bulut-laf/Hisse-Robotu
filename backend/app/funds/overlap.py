"""Portfolio overlap and exposure aggregation for sourced fund holdings."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Holding:
    fund_isin: str
    asset_id: str
    weight_pct: float
    asset_type: str = "equity"
    sector: str | None = None
    country: str | None = None
    currency: str | None = None
    source_url: str | None = None

    def __post_init__(self):
        if not self.fund_isin.strip():
            raise ValueError("fund_isin must not be blank")
        if not self.asset_id.strip():
            raise ValueError("asset_id must not be blank")
        if not 0 <= self.weight_pct <= 100:
            raise ValueError("weight_pct must be between 0 and 100")
        if self.source_url is not None and not self.source_url.startswith(("https://", "http://")):
            raise ValueError("source_url must be an absolute HTTP(S) URL")


def pairwise_overlap(first: Iterable[Holding], second: Iterable[Holding]) -> dict:
    """Sum min(weights) for shared asset IDs; weights are fund-level percentages."""
    a, b = _aggregate(first), _aggregate(second)
    if not a or not b:
        return {"comparable": False, "overlap_pct": None, "shared_assets": [], "reason": "missing_holdings"}
    shared = sorted(set(a) & set(b))
    overlap = sum(min(a[k], b[k]) for k in shared)
    return {"comparable": True, "overlap_pct": min(overlap, 100.0), "shared_assets": shared}


def exposure_breakdown(holdings: Iterable[Holding], dimension: str) -> dict:
    """Aggregate portfolio weights by sector/country/currency/asset_type for one fund."""
    allowed = {"sector", "country", "currency", "asset_type"}
    if dimension not in allowed:
        raise ValueError(f"dimension must be one of {sorted(allowed)}")
    rows = list(holdings)
    if not rows:
        return {"comparable": False, "dimension": dimension, "exposures": {}, "unclassified_weight_pct": None}
    totals: dict[str, float] = {}
    unclassified = 0.0
    for row in rows:
        value = getattr(row, dimension)
        if value is None or not str(value).strip():
            unclassified += row.weight_pct
        else:
            totals[str(value)] = totals.get(str(value), 0.0) + row.weight_pct
    return {
        "comparable": True,
        "dimension": dimension,
        "exposures": dict(sorted(totals.items(), key=lambda item: (-item[1], item[0].casefold()))),
        "unclassified_weight_pct": unclassified,
    }


def _aggregate(holdings: Iterable[Holding]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for holding in holdings:
        totals[holding.asset_id] = totals.get(holding.asset_id, 0.0) + holding.weight_pct
    return totals
