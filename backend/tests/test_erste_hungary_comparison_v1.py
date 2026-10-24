from __future__ import annotations

from decimal import Decimal

from backend.app.funds.international.erste_hungary_comparison import (
    comparison_to_snapshot,
    comparison_url_for_isin,
    parse_single_fund_comparison_html,
)


SAMPLE_HTML = """
<html><body>
<div>Deviza</div><div>Derivativ products</div>
<table>
<tr><td>Megnevez\u00e9s</td><td>ERSTE STOCK HUNGARY INDEX FUND</td></tr>
<tr><td>Torles</td></tr>
<tr><td>ISIN</td><td>HU0000704200</td></tr>
<tr><td>Alapkezel\u0151</td><td>ERSTE</td></tr>
<tr><td>Indul\u00e1s</td><td>2006.04.28.</td></tr>
<tr><td>Deviza</td><td>HUF</td></tr>
<tr><td>Akt. \u00e9vi hozam (%)</td><td>39.11%</td></tr>
<tr><td>1 \u00e9ves hozam (%)</td><td>53.95%</td></tr>
<tr><td>5 \u00e9ves hozam (%)</td><td>24.16%</td></tr>
<tr><td>1 \u00e9ves volatilit\u00e1s (%)</td><td>16.94%</td></tr>
<tr><td>3 \u00e9ves volatilit\u00e1s (%)</td><td>15.36%</td></tr>
<tr><td>5 \u00e9ves volatilit\u00e1s (%)</td><td>19.75%</td></tr>
<tr><td>1 \u00e9ves max drawdown (%)</td><td>-8.50%</td></tr>
<tr><td>5 \u00e9ves max drawdown (%)</td><td>-35.86%</td></tr>
<tr><td>\u00c1rfolyam</td><td>8.6598</td><td>2026.09.10.</td></tr>
<tr><td>Nett\u00f3 eszk\u00f6z\u00e9rt\u00e9k</td><td>48 567 103 749 HUF</td></tr>
<tr><td>Kateg\u00f3ria</td><td>R\u00e9szv\u00e9ny</td></tr>
<tr><td>Kock\u00e1zat</td><td>Magas</td></tr>
</table>
</body></html>
"""


def test_scoped_parser_ignores_global_ui_labels():
    fund = parse_single_fund_comparison_html(
        SAMPLE_HTML,
        source_url="https://example.invalid",
        expected_isin="HU0000704200",
    )

    assert fund.name == "ERSTE STOCK HUNGARY INDEX FUND"
    assert fund.fund_manager == "ERSTE"
    assert fund.currency == "HUF"
    assert fund.return_ytd == Decimal("0.3911")
    assert fund.return_1y == Decimal("0.5395")
    assert fund.return_5y == Decimal("0.2416")
    assert fund.volatility_1y == Decimal("0.1694")
    assert fund.volatility_3y == Decimal("0.1536")
    assert fund.volatility_5y == Decimal("0.1975")
    assert fund.max_drawdown_1y == Decimal("-0.085")
    assert fund.max_drawdown_5y == Decimal("-0.3586")
    assert fund.nav == Decimal("8.6598")
    assert fund.nav_date is not None
    assert fund.nav_date.isoformat() == "2026-09-10"
    assert fund.net_asset_value == Decimal("48567103749")
    assert fund.category_raw == "R\u00e9szv\u00e9ny"
    assert fund.risk_raw == "Magas"


def test_snapshot_mapping_preserves_identity():
    fund = parse_single_fund_comparison_html(
        SAMPLE_HTML,
        source_url="https://example.invalid",
        expected_isin="HU0000704200",
    )
    snapshot = comparison_to_snapshot(fund)
    assert snapshot.canonical_fund_id == "fund:isin:HU0000704200"
    assert snapshot.market == "HU"
    assert snapshot.distribution == "ERSTE_HUNGARY"
    assert snapshot.currency == "HUF"


def test_comparison_url_is_deterministic():
    assert comparison_url_for_isin("hu0000704200") == (
        "https://www.erstemarket.hu/befektetesi_alapok/"
        "osszehasonlitas?funds=HU0000704200"
    )

def test_missing_inception_does_not_consume_next_label():
    html = """
    <table>
      <tr><td>Megnevez\u00e9s</td><td>CPR INVEST - HYDROGEN- A USD-ACC</td></tr>
      <tr><td>ISIN</td><td>LU2450391748</td></tr>
      <tr><td>Alapkezel\u0151</td><td>Amundi (Lux)</td></tr>
      <tr><td>Indul\u00e1s</td></tr>
      <tr><td>Deviza</td><td>USD</td></tr>
      <tr><td>Akt. \u00e9vi hozam (%)</td><td>11.34%</td></tr>
      <tr><td>1 \u00e9ves hozam (%)</td><td>20.69%</td></tr>
      <tr><td>\u00c1rfolyam</td><td>154.78</td><td>2026.09.22.</td></tr>
      <tr><td>Nett\u00f3 eszk\u00f6z\u00e9rt\u00e9k</td><td>1 764 555 USD</td></tr>
      <tr><td>Kateg\u00f3ria</td><td>R\u00e9szv\u00e9ny</td></tr>
      <tr><td>Kock\u00e1zat</td><td>Magas</td></tr>
    </table>
    """

    fund = parse_single_fund_comparison_html(
        html,
        source_url="https://example.invalid",
        expected_isin="LU2450391748",
    )

    assert fund.inception_date is None
    assert fund.currency == "USD"
    assert fund.return_1y == Decimal("0.2069")

def test_missing_risk_does_not_consume_documents_label():
    html = """
    <table>
      <tr><td>Megnevez\u00e9s</td><td>Sample Fund</td></tr>
      <tr><td>ISIN</td><td>LU0000000001</td></tr>
      <tr><td>Alapkezel\u0151</td><td>Manager</td></tr>
      <tr><td>Deviza</td><td>EUR</td></tr>
      <tr><td>\u00c1rfolyam</td><td>100.0</td><td>2026.09.23.</td></tr>
      <tr><td>Kateg\u00f3ria</td><td>R\u00e9szv\u00e9ny</td></tr>
      <tr><td>Kock\u00e1zat</td></tr>
      <tr><td>Dokumentumok</td></tr>
    </table>
    """

    fund = parse_single_fund_comparison_html(
        html,
        source_url="https://example.invalid",
        expected_isin="LU0000000001",
    )

    assert fund.risk_raw is None

def test_valid_risk_values_are_preserved():
    html = """
    <table>
      <tr><td>Megnevez\u00e9s</td><td>Sample Fund</td></tr>
      <tr><td>ISIN</td><td>LU0000000002</td></tr>
      <tr><td>Alapkezel\u0151</td><td>Manager</td></tr>
      <tr><td>Deviza</td><td>EUR</td></tr>
      <tr><td>\u00c1rfolyam</td><td>100.0</td><td>2026.09.23.</td></tr>
      <tr><td>Kateg\u00f3ria</td><td>R\u00e9szv\u00e9ny</td></tr>
      <tr><td>Kock\u00e1zat</td><td>K\u00f6zepes</td></tr>
    </table>
    """

    fund = parse_single_fund_comparison_html(
        html,
        source_url="https://example.invalid",
        expected_isin="LU0000000002",
    )

    assert fund.risk_raw == "K\u00f6zepes"