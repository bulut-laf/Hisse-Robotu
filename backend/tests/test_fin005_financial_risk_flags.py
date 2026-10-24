from datetime import datetime
from decimal import Decimal

from backend.app.analysis.financial_risk_flags import FLAG_ORDER, calculate_financial_risk_flags
from backend.app.data.historical_financial_series import build_historical_financial_series
from backend.app.data.kap_financial_xls import import_kap_financial_xls_bytes

SAMPLE = b'''<html><body>
<h1>TUPRAS TEST A.S.</h1>
<div>G\xc3\xb6nderim Tarihi:04.08.2026 18:24:32</div>
<div>Y\xc4\xb1l:2026</div><div>Periyot:2</div>
<table class="financial-header-table"><tr><td>Sunum Para Birimi</td><td>1.000 TL</td></tr><tr><td>Finansal Tablo Niteli\xc4\x9fi</td><td>Konsolide</td></tr></table>
<table class="financial-table"><tr><td></td><td class="context-header">Cari D\xc3\xb6nem<br>30.06.2026</td><td class="context-header">\xc3\x96nceki D\xc3\xb6nem<br>31.12.2025</td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>Finansal Durum Tablosu (Bilan\xc3\xa7o)</td></tr></table></td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>Nakit ve Nakit Benzerleri</td></tr></table></td><td></td><td class="taxonomy-context-value"><div title="195840940">195.840.940</div></td><td class="taxonomy-context-value"><div title="126280395">126.280.395</div></td></tr><tr><td></td><td class="taxonomy-field-title"><table><tr><td>Ticari Alacaklar</td></tr></table></td><td></td><td class="taxonomy-context-value"><div title="78747644">x</div></td><td class="taxonomy-context-value"><div title="62120487">x</div></td></tr><tr><td></td><td class="taxonomy-field-title"><table><tr><td>Stoklar</td></tr></table></td><td></td><td class="taxonomy-context-value"><div title="97044745">x</div></td><td class="taxonomy-context-value"><div title="73181263">x</div></td></tr>
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
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>Maddi ve Maddi Olmayan Duran Varl\xc4\xb1klar\xc4\xb1n Al\xc4\xb1m\xc4\xb1ndan Kaynaklanan Nakit \xc3\x87\xc4\xb1k\xc4\xb1\xc5\x9flar\xc4\xb1</td></tr></table></td><td></td><td class="taxonomy-context-value"><div title="-11858044">x</div></td><td class="taxonomy-context-value"><div title="-10941299">x</div></td></tr></table></body></html>'''


def _series():
    imported = import_kap_financial_xls_bytes(SAMPLE, source_name="TUPRS_1643116_2026_2.xls")
    return build_historical_financial_series([imported])


def _flags(a):
    return {f.code: f for f in a.flags}


def _metrics(a):
    return {m.code: m.value for m in a.metrics}


def test_fin005_tuprs_like_reference_is_low_risk_and_explainable():
    a = calculate_financial_risk_flags(_series())
    f = _flags(a)
    m = _metrics(a)
    assert a.locked is False
    assert a.risk_score == 0
    assert a.risk_level == "LOW"
    assert f["NET_DEBT_ACCELERATION"].status == "INACTIVE"
    assert f["MARGIN_COMPRESSION"].status == "INACTIVE"
    assert f["NEGATIVE_OPERATING_CASH_FLOW"].status == "INACTIVE"
    assert f["PROFIT_WITHOUT_CASH"].status == "INACTIVE"
    assert f["WORKING_CAPITAL_STRESS"].status == "INACTIVE"
    assert m["OPERATING_MARGIN_DELTA"] == Decimal("5.00")
    assert "NET_CASH" in a.positive_evidence
    assert "MARGIN_EXPANSION" in a.positive_evidence
    assert "STRONG_CASH_CONVERSION" in a.positive_evidence


def test_fin005_does_not_fake_same_date_yoy_balance_flags():
    a = calculate_financial_risk_flags(_series())
    f = _flags(a)
    assert f["RECEIVABLES_OUTPACE_REVENUE"].status == "NOT_EVALUATED"
    assert f["INVENTORY_BUILDUP"].status == "NOT_EVALUATED"
    assert "aynı tarihli" in f["RECEIVABLES_OUTPACE_REVENUE"].reason.casefold()


def test_fin005_does_not_substitute_finance_expense_for_interest_expense():
    a = calculate_financial_risk_flags(_series())
    f = _flags(a)
    assert f["INTEREST_COVERAGE_STRESS"].status == "NOT_EVALUATED"
    assert "saf faiz gideri" in f["INTEREST_COVERAGE_STRESS"].reason.casefold()


def test_fin005_deferred_note_and_share_flags_are_visible_not_evaluated():
    a = calculate_financial_risk_flags(_series())
    f = _flags(a)
    for code in ("DILUTION_RISK", "AUDITOR_WARNING", "GOING_CONCERN_WARNING", "RELATED_PARTY_EXPOSURE", "CONTINGENT_LIABILITY_RISK"):
        assert f[code].status == "NOT_EVALUATED"
    assert tuple(x.code for x in a.flags) == FLAG_ORDER


def test_fin005_point_in_time_fail_closed_before_publication():
    a = calculate_financial_risk_flags(_series(), as_of=datetime(2026, 8, 1, 12, 0, 0))
    assert a.locked is True
    assert a.risk_score is None
    assert a.risk_level == "UNKNOWN"


def test_fin005_not_buy_sell_signal():
    a = calculate_financial_risk_flags(_series())
    assert "alım/satım sinyali değildir" in a.explanation.casefold()
    assert "not_evaluated" in a.explanation.casefold()
