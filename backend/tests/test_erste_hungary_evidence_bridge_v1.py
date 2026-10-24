from decimal import Decimal

from backend.app.funds.international.erste_hungary_evidence_bridge import (
    bridge_erste_f1,
    bridge_from_history_pair,
    build_erste_f1_input,
)


def test_bridge_builds_provider_independent_fund_id():
    value = build_erste_f1_input(
        isin="LU0000000001",
        category_normalized="EQUITY",
        latest_rank_percentile=Decimal("0.95"),
        rank_change=7,
    )

    assert value.canonical_fund_id == "fund:isin:LU0000000001"
    assert value.category_id == "EQUITY"
    assert value.category_rank_percentile == Decimal("0.95")
    assert value.category_rank_change == 7


def test_bridge_does_not_force_unavailable_families():
    value = build_erste_f1_input(
        isin="LU0000000002",
        category_normalized="BOND",
        latest_rank_percentile=Decimal("0.50"),
        rank_change=0,
    )

    assert value.return_1m is None
    assert value.return_3m is None
    assert value.return_6m is None
    assert value.volatility_percentile is None
    assert value.max_drawdown is None
    assert value.fund_size_change is None
    assert value.investor_change is None
    assert value.net_flow_ratio is None
    assert value.total_expense_ratio is None
    assert value.regime_fit is None
    assert value.allocation_known is False


def test_history_pair_uses_positive_change_for_improving_rank():
    old = {
        "isin": "LU0000000003",
        "category_normalized": "EQUITY",
        "rank_position": 50,
        "rank_percentile": "0.80",
    }
    new = {
        "isin": "LU0000000003",
        "category_normalized": "EQUITY",
        "rank_position": 35,
        "rank_percentile": "0.90",
    }

    result = bridge_from_history_pair(old, new)

    assert result.evidence_input.category_rank_change == 15
    assert result.evidence_input.category_rank_percentile == Decimal("0.90")
    assert any("rank_change=15" in fact for fact in result.mapped_f1_facts)


def test_mapper_generates_f1_without_trade_authority():
    result = bridge_erste_f1(
        isin="LU0000000004",
        category_normalized="MIXED",
        latest_rank_percentile=Decimal("0.75"),
        rank_change=-3,
    )

    assert result.mapped_f1_facts
    assert result.evidence_input.canonical_fund_id.startswith("fund:isin:")