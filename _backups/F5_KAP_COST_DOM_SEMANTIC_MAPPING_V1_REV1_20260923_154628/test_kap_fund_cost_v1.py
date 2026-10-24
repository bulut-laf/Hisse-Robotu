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



def test_parse_kap_fund_cost_metrics_uses_visible_turkish_current_period_value():
    html = (
        '<table><tr>'
        '<td class="taxonomy-field-name-cell">oda_FundTotalExpenseRatioRealizedAtTheEndOfPeriod|</td>'
        '<td></td><td></td><td></td><td></td><td>TR</td><td>EN</td>'
        '<td class="taxonomy-context-value col-order-class-3 multi-language-content content-tr">% 1,4</td>'
        '<td class="taxonomy-context-value col-order-class-4 multi-language-content content-en">% 0,46</td>'
        '</tr><tr>'
        '<td class="taxonomy-field-name-cell">oda_NetFundTotalExpenseRatioRealizedAtTheEndOfPeriod|</td>'
        '<td></td><td></td><td></td><td></td><td>TR</td><td>EN</td>'
        '<td class="taxonomy-context-value col-order-class-3 multi-language-content content-tr">% 1,4</td>'
        '<td class="taxonomy-context-value col-order-class-4 multi-language-content content-en">% 0,47</td>'
        '</tr>'
        '<tr><td>oda_AnnualMaximumFundTotalExpenseRatio|</td><td></td><td></td><td></td><td></td><td></td><td></td>'
        '<td class="taxonomy-context-value col-order-class-3 multi-language-content content-tr">% 3,65</td>'
        '<td class="taxonomy-context-value col-order-class-4 multi-language-content content-en">% 2,19</td></tr>'
        '<tr><td>oda_MaximumFundTotalExpsenseRatioThatFallToRelatedPeriod|</td><td></td><td></td><td></td><td></td><td></td><td></td>'
        '<td class="taxonomy-context-value col-order-class-3 multi-language-content content-tr">% 1,825</td>'
        '<td class="taxonomy-context-value col-order-class-4 multi-language-content content-en">% 1,095</td></tr>'
        '<tr><td>oda_AnnualManagementFee|</td><td></td><td></td><td></td><td></td><td></td><td></td>'
        '<td class="taxonomy-context-value col-order-class-3 multi-language-content content-tr">% 87,97</td>'
        '<td class="taxonomy-context-value col-order-class-4 multi-language-content content-en">% 0,51</td></tr>'
        '</table>'
    )
    result = parse_kap_fund_cost_metrics(
        html,
        fund_code="PHE",
        notification_id="1629937",
    )
    assert result.current_period_realized_expense_ratio == Decimal("0.014")
    assert result.current_period_net_realized_expense_ratio == Decimal("0.014")
