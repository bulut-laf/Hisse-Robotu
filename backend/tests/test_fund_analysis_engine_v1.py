from dataclasses import replace
from decimal import Decimal

import pytest

from backend.app.funds.analysis_engine import FundAnalysisClass, analyze_fund, analyze_funds
from backend.app.funds.evidence_mapper import FundEvidenceInput, map_fund_evidence


def source(**changes):
    value = FundEvidenceInput(
        canonical_fund_id="fund:tefas:AAA", category_id="equity",
        category_rank_percentile=Decimal("0.8"), category_rank_change=2,
        return_1m=Decimal("0.02"), return_3m=Decimal("0.05"), return_6m=Decimal("0.10"),
        volatility_percentile=Decimal("0.4"), max_drawdown=Decimal("-0.08"),
        fund_size_change=Decimal("0.05"), investor_change=Decimal("0.04"), net_flow_ratio=Decimal("0.03"),
        total_expense_ratio=Decimal("0.015"), regime_fit=Decimal("0.8"), allocation_known=True,
    )
    return replace(value, **changes)


def result(**changes):
    return analyze_fund(map_fund_evidence(source(**changes)))


def test_a_requires_broad_strength_and_no_caution():
    item = result()
    assert item.classification is FundAnalysisClass.A
    assert item.automatic_trade_authority == "NONE" and not item.forced_fill


def test_b_is_developing_multi_family_support():
    item = result(volatility_percentile=Decimal("0.6"), max_drawdown=Decimal("-0.15"),
                  total_expense_ratio=Decimal("0.03"), regime_fit=Decimal("0.5"))
    assert item.classification is FundAnalysisClass.B


def test_c_is_watch_without_forcing_stronger_class():
    item = result(category_rank_percentile=Decimal("0.5"), category_rank_change=0,
                  return_1m=Decimal("0"), return_3m=Decimal("0.01"), return_6m=Decimal("0.02"),
                  volatility_percentile=Decimal("0.6"), max_drawdown=Decimal("-0.15"),
                  fund_size_change=Decimal("0"), investor_change=Decimal("0"), net_flow_ratio=Decimal("0"),
                  total_expense_ratio=Decimal("0.03"), regime_fit=Decimal("0.5"))
    assert item.classification is FundAnalysisClass.C


def test_d_requires_multi_family_weakening():
    item = result(category_rank_percentile=Decimal("0.2"), category_rank_change=-4,
                  return_1m=Decimal("-0.02"), return_3m=Decimal("-0.03"))
    assert item.classification is FundAnalysisClass.D


def test_x_for_unmapped_or_insufficient_evidence():
    assert result(category_id=None).classification is FundAnalysisClass.X
    assert result(return_1m=None, volatility_percentile=None, fund_size_change=None,
                  investor_change=None, total_expense_ratio=None).classification is FundAnalysisClass.X


def test_no_forced_fill_and_order_is_deterministic():
    first = map_fund_evidence(source(canonical_fund_id="fund:tefas:BBB"))
    second = map_fund_evidence(source(canonical_fund_id="fund:tefas:AAA"))
    output = analyze_funds((first, second))
    assert tuple(item.canonical_fund_id for item in output) == ("fund:tefas:AAA", "fund:tefas:BBB")
    assert all(not item.forced_fill for item in output)


def test_duplicate_fund_is_rejected_not_silently_merged():
    item = map_fund_evidence(source())
    with pytest.raises(ValueError, match="DUPLICATE_FUND"):
        analyze_funds((item, item))
