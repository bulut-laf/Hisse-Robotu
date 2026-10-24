from __future__ import annotations

from decimal import Decimal
from typing import Any

from backend.app.funds.evidence_mapper import FundEvidenceInput, map_fund_evidence


F3_BRIDGE_VERSION = "erste-hungary-f3-evidence-bridge-v1"


def category_volatility_percentiles(
    rows: list[dict[str, Any]],
) -> dict[str, Decimal]:
    grouped: dict[str, list[tuple[str, Decimal]]] = {}

    for row in rows:
        isin = str(row.get("isin") or "").strip().upper()
        category = str(row.get("category_normalized") or "").strip()
        raw = row.get("volatility_1y")
        if not isin or not category or raw in (None, "", "-"):
            continue
        grouped.setdefault(category, []).append((isin, Decimal(str(raw))))

    result: dict[str, Decimal] = {}

    for items in grouped.values():
        values = sorted(value for _, value in items)
        n = len(values)

        for isin, value in items:
            if n == 1:
                percentile = Decimal("0.5")
            else:
                # Lower volatility is better. Percentile expresses relative
                # risk position from low (0) to high (1).
                lower_count = sum(1 for candidate in values if candidate < value)
                equal_count = sum(1 for candidate in values if candidate == value)
                mid_rank = (
                    Decimal(lower_count)
                    + (Decimal(equal_count) - Decimal("1")) / Decimal("2")
                )
                percentile = mid_rank / Decimal(n - 1)

            result[isin] = percentile

    return result


def build_f1_f3_input(
    *,
    isin: str,
    category_normalized: str,
    category_rank_percentile: Decimal | None,
    category_rank_change: int | None,
    volatility_percentile: Decimal | None,
    max_drawdown_1y: Decimal | None,
) -> FundEvidenceInput:
    return FundEvidenceInput(
        canonical_fund_id=f"fund:isin:{isin.strip().upper()}",
        category_id=category_normalized,
        category_rank_percentile=category_rank_percentile,
        category_rank_change=category_rank_change,
        return_1m=None,
        return_3m=None,
        return_6m=None,
        volatility_percentile=volatility_percentile,
        max_drawdown=max_drawdown_1y,
        fund_size_change=None,
        investor_change=None,
        net_flow_ratio=None,
        total_expense_ratio=None,
        regime_fit=None,
        allocation_known=False,
    )


def mapped_f3_state(value: FundEvidenceInput) -> str:
    mapped = map_fund_evidence(value)
    f3 = next(item for item in mapped.evidence if item.family == "F3")
    return str(f3.state)