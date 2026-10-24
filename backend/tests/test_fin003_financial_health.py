from datetime import datetime
from decimal import Decimal

from backend.app.analysis.financial_health import calculate_financial_health
from backend.app.data.historical_financial_series import build_historical_financial_series
from backend.app.data.kap_financial_xls import import_kap_financial_xls_bytes


SAMPLE = b'''<html><body>
<h1>TUPRAS TEST A.S.</h1>
<div>G\xc3\xb6nderim Tarihi:04.08.2026 18:24:32</div>
<div>Y\xc4\xb1l:2026</div><div>Periyot:2</div>
<table class="financial-header-table"><tr><td>Sunum Para Birimi</td><td>1.000 TL</td></tr><tr><td>Finansal Tablo Niteli\xc4\x9fi</td><td>Konsolide</td></tr></table>
<table class="financial-table"><tr><td></td><td class="context-header">Cari D\xc3\xb6nem<br>30.06.2026</td><td class="context-header">\xc3\x96nceki D\xc3\xb6nem<br>31.12.2025</td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>Finansal Durum Tablosu (Bilan\xc3\xa7o)</td></tr></table></td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>Nakit ve Nakit Benzerleri</td></tr></table></td><td></td><td class="taxonomy-context-value"><div title="195840940">195.840.940</div></td><td class="taxonomy-context-value"><div title="126280395">126.280.395</div></td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>D\xc3\x96NEN VARLIKLAR</td></tr></table></td><td></td><td class="taxonomy-context-value"><div title="439480874">439.480.874</div></td><td class="taxonomy-context-value"><div title="279005365">279.005.365</div></td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>TOPLAM VARLIKLAR</td></tr></table></td><td></td><td class="taxonomy-context-value"><div title="859987516">859.987.516</div></td><td class="taxonomy-context-value"><div title="697096555">697.096.555</div></td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>K\xc4\xb1sa Vadeli Bor\xc3\xa7lanmalar</td></tr></table></td><td></td><td class="taxonomy-context-value"><div title="17579248">17.579.248</div></td><td class="taxonomy-context-value"><div title="10547702">10.547.702</div></td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>Uzun Vadeli Bor\xc3\xa7lanmalar\xc4\xb1n K\xc4\xb1sa Vadeli K\xc4\xb1s\xc4\xb1mlar\xc4\xb1</td></tr></table></td><td></td><td class="taxonomy-context-value"><div title="14178331">14.178.331</div></td><td class="taxonomy-context-value"><div title="15147930">15.147.930</div></td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>KISA VADEL\xc4\xb0 Y\xc3\x9cK\xc3\x9cML\xc3\x9cL\xc3\x9cKLER</td></tr></table></td><td></td><td class="taxonomy-context-value"><div title="325369321">325.369.321</div></td><td class="taxonomy-context-value"><div title="199892086">199.892.086</div></td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>Uzun Vadeli Bor\xc3\xa7lanmalar</td></tr></table></td><td></td><td class="taxonomy-context-value"><div title="36443100">36.443.100</div></td><td class="taxonomy-context-value"><div title="33477157">33.477.157</div></td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>UZUN VADEL\xc4\xb0 Y\xc3\x9cK\xc3\x9cML\xc3\x9cL\xc3\x9cKLER</td></tr></table></td><td></td><td class="taxonomy-context-value"><div title="71311414">71.311.414</div></td><td class="taxonomy-context-value"><div title="61702421">61.702.421</div></td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>TOPLAM \xc3\x96ZKAYNAKLAR</td></tr></table></td><td></td><td class="taxonomy-context-value"><div title="463306781">463.306.781</div></td><td class="taxonomy-context-value"><div title="435502048">435.502.048</div></td></tr>
</table>
<table class="financial-table"><tr><td></td><td class="context-header">Cari D\xc3\xb6nem<br>01.01.2026 - 30.06.2026</td><td class="context-header">\xc3\x96nceki D\xc3\xb6nem<br>01.01.2025 - 30.06.2025</td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>Kar veya Zarar Tablosu</td></tr></table></td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>Has\xc4\xb1lat</td></tr></table></td><td></td><td class="taxonomy-context-value"><div title="662788010">662.788.010</div></td><td class="taxonomy-context-value"><div title="464119398">464.119.398</div></td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>BR\xc3\x9cT KAR (ZARAR)</td></tr></table></td><td></td><td class="taxonomy-context-value"><div title="84125684">84.125.684</div></td><td class="taxonomy-context-value"><div title="41987994">41.987.994</div></td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>ESAS FAAL\xc4\xb0YET KARI (ZARARI)</td></tr></table></td><td></td><td class="taxonomy-context-value"><div title="59025244">59.025.244</div></td><td class="taxonomy-context-value"><div title="18160918">18.160.918</div></td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>D\xc3\x96NEM KARI (ZARARI)</td></tr></table></td><td></td><td class="taxonomy-context-value"><div title="50272473">50.272.473</div></td><td class="taxonomy-context-value"><div title="11981560">11.981.560</div></td></tr>
</table>
<table class="financial-table"><tr><td></td><td class="context-header">Cari D\xc3\xb6nem<br>01.01.2026 - 30.06.2026</td><td class="context-header">\xc3\x96nceki D\xc3\xb6nem<br>01.01.2025 - 30.06.2025</td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>Nakit Ak\xc4\xb1\xc5\x9f Tablosu</td></tr></table></td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>\xc4\xb0\xc5\x9eLETME FAAL\xc4\xb0YETLER\xc4\xb0NDEN NAK\xc4\xb0T AKI\xc5\x9eLARI</td></tr></table></td><td></td><td class="taxonomy-context-value"><div title="132366363">132.366.363</div></td><td class="taxonomy-context-value"><div title="15012559">15.012.559</div></td></tr>
</table></body></html>'''


def _series():
    imported = import_kap_financial_xls_bytes(SAMPLE, source_name="TUPRS_1643116_2026_2.xls")
    return build_historical_financial_series([imported])


def _metric_map(assessment):
    return {metric.code: metric.value for metric in assessment.metrics}


def test_fin003_tuprs_reference_health_is_explainable_and_complete():
    assessment = calculate_financial_health(_series())
    metrics = _metric_map(assessment)

    assert assessment.locked is False
    assert assessment.data_coverage == Decimal("100.00")
    assert assessment.score == 94
    assert assessment.grade == "VERY_STRONG"
    assert assessment.financial_risk == "LOW"
    assert metrics["CURRENT_RATIO"] == Decimal("1.35")
    assert metrics["CASH_RATIO"] == Decimal("0.60")
    assert metrics["EQUITY_RATIO"] == Decimal("53.87")
    assert metrics["FINANCIAL_DEBT"] == Decimal("68200679")
    assert metrics["NET_DEBT"] == Decimal("-127640261")
    assert metrics["OPERATING_MARGIN"] == Decimal("8.91")
    assert metrics["NET_MARGIN"] == Decimal("7.59")
    assert metrics["OCF_TO_NET_INCOME"] == Decimal("2.63")
    assert "NET_CASH" in assessment.positive_evidence
    assert "STRONG_CASH_CONVERSION" in assessment.positive_evidence
    assert "CURRENT_RATIO_BELOW_1_5" in assessment.cautions


def test_fin003_components_preserve_design_weights():
    assessment = calculate_financial_health(_series())
    weights = {component.code: component.maximum_score for component in assessment.components}
    assert weights == {
        "LIQUIDITY": 15,
        "BALANCE_SHEET": 20,
        "PROFITABILITY": 20,
        "CASH_QUALITY": 20,
        "CAPITAL_EFFICIENCY": 15,
        "STABILITY": 10,
    }
    assert sum(weights.values()) == 100


def test_fin003_is_point_in_time_safe_before_publication():
    assessment = calculate_financial_health(_series(), as_of=datetime(2026, 8, 1, 12, 0, 0))
    assert assessment.locked is True
    assert assessment.score is None
    assert assessment.grade == "DATA_INSUFFICIENT"
    assert assessment.financial_risk == "UNKNOWN"


def test_fin003_after_publication_matches_current_assessment():
    series = _series()
    current = calculate_financial_health(series)
    as_of = calculate_financial_health(series, as_of=datetime(2026, 8, 5, 0, 0, 0))
    assert as_of.score == current.score
    assert as_of.grade == current.grade
    assert _metric_map(as_of)["NET_DEBT"] == _metric_map(current)["NET_DEBT"]


def test_fin003_does_not_emit_buy_sell_signal_language():
    assessment = calculate_financial_health(_series())
    text = assessment.explanation.casefold()
    assert "alım/satım sinyali değildir" in text
