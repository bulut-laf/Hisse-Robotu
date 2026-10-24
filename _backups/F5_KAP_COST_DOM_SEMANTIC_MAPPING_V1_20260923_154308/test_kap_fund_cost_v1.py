from decimal import Decimal

from backend.app.funds.kap_fund_cost import (
    discover_kap_fund_cost_disclosures,
    parse_kap_fund_cost_metrics,
)


def test_parse_kap_fund_cost_metrics_preserves_all_percentage_columns():
    html = """
    oda_AnnualMaximumFundTotalExpenseRatio| Yıllık Azami Fon Toplam Gider Oranı (%) % 3,65 % 2,19
    oda_MaximumFundTotalExpsenseRatioThatFallToRelatedPeriod| İlgili Döneme Denk Gelen Azami (%) % 1,825 % 1,095
    oda_FundTotalExpenseRatioRealizedAtTheEndOfPeriod| Gerçekleşen Fon Toplam Gider Oranı (%) % 1,4 % 0,46
    oda_NetFundTotalExpenseRatioRealizedAtTheEndOfPeriod| Net Fon Toplam Gider Oranı (%) % 1,4 % 0,47
    oda_AnnualManagementFee| Yönetim Ücreti (Yıllık) (%) % 87,97 % 0,51
    oda_Other| next
    """
    result = parse_kap_fund_cost_metrics(
        html,
        fund_code="PHE",
        notification_id="1629937",
    )
    assert result.annual_maximum_expense_ratio_values == (
        Decimal("0.0365"), Decimal("0.0219")
    )
    assert result.period_maximum_expense_ratio_values == (
        Decimal("0.01825"), Decimal("0.01095")
    )
    assert result.realized_expense_ratio_values == (
        Decimal("0.014"), Decimal("0.0046")
    )
    assert result.realized_net_expense_ratio_values == (
        Decimal("0.014"), Decimal("0.0047")
    )
    assert result.annual_management_fee_values == (
        Decimal("0.8797"), Decimal("0.0051")
    )
