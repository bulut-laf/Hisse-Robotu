from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from backend.app.funds.evidence_mapper import (
    FundEvidenceInput,
    map_fund_evidence,
)


BRIDGE_VERSION = "erste-hungary-f1-evidence-bridge-v1"


@dataclass(frozen=True, slots=True)
class ErsteF1BridgeResult:
    evidence_input: FundEvidenceInput
    mapped_f1_state: str
    mapped_f1_facts: tuple[str, ...]
    mapped_f1_missing_fields: tuple[str, ...]


def build_erste_f1_input(
    *,
    isin: str,
    category_normalized: str,
    latest_rank_percentile: Decimal,
    rank_change: int,
) -> FundEvidenceInput:
    return FundEvidenceInput(
        canonical_fund_id=f"fund:isin:{isin.strip().upper()}",
        category_id=category_normalized,
        category_rank_percentile=Decimal(str(latest_rank_percentile)),
        category_rank_change=int(rank_change),
        return_1m=None,
        return_3m=None,
        return_6m=None,
        volatility_percentile=None,
        max_drawdown=None,
        fund_size_change=None,
        investor_change=None,
        net_flow_ratio=None,
        total_expense_ratio=None,
        regime_fit=None,
        allocation_known=False,
    )


def bridge_erste_f1(
    *,
    isin: str,
    category_normalized: str,
    latest_rank_percentile: Decimal,
    rank_change: int,
) -> ErsteF1BridgeResult:
    evidence_input = build_erste_f1_input(
        isin=isin,
        category_normalized=category_normalized,
        latest_rank_percentile=latest_rank_percentile,
        rank_change=rank_change,
    )

    mapped = map_fund_evidence(evidence_input)
    f1 = next(item for item in mapped.evidence if item.family == "F1")

    return ErsteF1BridgeResult(
        evidence_input=evidence_input,
        mapped_f1_state=str(f1.state),
        mapped_f1_facts=tuple(f1.facts),
        mapped_f1_missing_fields=tuple(f1.missing_fields),
    )


def bridge_from_history_pair(
    old: dict[str, Any],
    new: dict[str, Any],
) -> ErsteF1BridgeResult:
    old_rank = int(old["rank_position"])
    new_rank = int(new["rank_position"])

    return bridge_erste_f1(
        isin=str(new["isin"]),
        category_normalized=str(new["category_normalized"]),
        latest_rank_percentile=Decimal(str(new["rank_percentile"])),
        rank_change=old_rank - new_rank,
    )