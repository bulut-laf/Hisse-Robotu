from dataclasses import replace
from decimal import Decimal

from backend.app.funds.evidence_mapper import EvidenceState, FundEvidenceInput, map_fund_evidence


def sample(**changes):
    value = FundEvidenceInput(
        canonical_fund_id="fund:tefas:TST", category_id="debt",
        category_rank_percentile=Decimal("0.8"), category_rank_change=3,
        return_1m=Decimal("0.02"), return_3m=Decimal("0.06"), return_6m=Decimal("0.12"),
        volatility_percentile=Decimal("0.4"), max_drawdown=Decimal("-0.08"),
        fund_size_change=Decimal("0.10"), investor_change=Decimal("0.05"), net_flow_ratio=Decimal("0.03"),
        total_expense_ratio=Decimal("0.015"), regime_fit=Decimal("0.8"), allocation_known=True,
    )
    return replace(value, **changes)


def test_all_five_independent_families_map_in_stable_order():
    result = map_fund_evidence(sample())
    assert tuple(item.family for item in result.evidence) == ("F1", "F2", "F3", "F4", "F5")
    assert all(item.state is EvidenceState.POSITIVE for item in result.evidence)
    assert result.available_family_count == 5


def test_unmapped_category_does_not_force_fill():
    result = map_fund_evidence(sample(category_id=None))
    assert result.category_mapping_state == "UNMAPPED"
    assert result.evidence[0].state is EvidenceState.UNAVAILABLE


def test_missing_values_are_not_neutral_or_zero():
    result = map_fund_evidence(sample(return_3m=None))
    assert result.evidence[1].state is EvidenceState.UNAVAILABLE
    assert result.evidence[1].missing_fields == ("return_3m",)


def test_f4_can_be_partial_but_requires_two_independent_facts():
    partial = map_fund_evidence(sample(net_flow_ratio=None)).evidence[3]
    unavailable = map_fund_evidence(sample(net_flow_ratio=None, investor_change=None)).evidence[3]
    assert partial.state is EvidenceState.POSITIVE and partial.missing_fields == ("net_flow_ratio",)
    assert unavailable.state is EvidenceState.UNAVAILABLE


def test_caution_paths_are_deterministic():
    result = map_fund_evidence(sample(
        category_rank_percentile=Decimal("0.2"), category_rank_change=-4,
        return_1m=Decimal("-0.02"), return_3m=Decimal("-0.03"),
        volatility_percentile=Decimal("0.9"), max_drawdown=Decimal("-0.25"),
        fund_size_change=Decimal("-0.1"), investor_change=Decimal("-0.1"),
        total_expense_ratio=Decimal("0.05"), regime_fit=Decimal("0.2"),
    ))
    assert all(item.state is EvidenceState.CAUTION for item in result.evidence)


def test_input_order_is_irrelevant_and_mapping_repeats_exactly():
    assert map_fund_evidence(sample()) == map_fund_evidence(sample())
