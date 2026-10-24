from decimal import Decimal

from backend.app.funds.evidence_mapper import EvidenceState, FundEvidenceInput
from backend.app.funds.international.erste_hungary_f4_bridge import (
    derive_f4_state,
    derive_fund_size_change,
    inject_f4_fields,
)


def test_f4_positive_requires_both_fields_positive():
    assert derive_f4_state(
        fund_size_change=Decimal("0.01"),
        net_flow_ratio=Decimal("0.02"),
    ) == EvidenceState.POSITIVE


def test_f4_caution_requires_both_fields_negative():
    assert derive_f4_state(
        fund_size_change=Decimal("-0.01"),
        net_flow_ratio=Decimal("-0.02"),
    ) == EvidenceState.CAUTION


def test_f4_mixed_is_neutral():
    assert derive_f4_state(
        fund_size_change=Decimal("0.01"),
        net_flow_ratio=Decimal("-0.02"),
    ) == EvidenceState.NEUTRAL


def test_f4_requires_two_fields():
    assert derive_f4_state(
        fund_size_change=Decimal("0.01"),
        net_flow_ratio=None,
    ) == EvidenceState.UNAVAILABLE


def test_fund_size_change_uses_same_source_nav_pair():
    assert derive_fund_size_change(
        Decimal("100"),
        Decimal("105"),
    ) == Decimal("0.05")


def test_inject_f4_preserves_existing_fields():
    base = FundEvidenceInput(
        canonical_fund_id="fund:isin:TEST00000001",
        category_id="EQUITY",
        category_rank_percentile=Decimal("0.8"),
        category_rank_change=5,
        return_1m=Decimal("0.01"),
        return_3m=Decimal("0.02"),
        return_6m=Decimal("0.03"),
        volatility_percentile=Decimal("0.4"),
        max_drawdown=Decimal("-0.05"),
        fund_size_change=None,
        investor_change=None,
        net_flow_ratio=None,
        total_expense_ratio=None,
        regime_fit=None,
        allocation_known=False,
    )
    value = inject_f4_fields(
        base,
        fund_size_change=Decimal("0.01"),
        net_flow_ratio=Decimal("0.02"),
    )
    assert value.return_1m == Decimal("0.01")
    assert value.volatility_percentile == Decimal("0.4")
    assert value.fund_size_change == Decimal("0.01")
    assert value.net_flow_ratio == Decimal("0.02")
    assert value.investor_change is None