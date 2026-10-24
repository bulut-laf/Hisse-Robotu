from decimal import Decimal

from backend.app.data.kap_financial_xls import import_kap_financial_xls_bytes


SAMPLE = b'''<html><body>
<h1>TUPRAS TEST A.S.</h1>
<div>G\xc3\xb6nderim Tarihi:04.08.2026 18:24:32</div>
<div>Y\xc4\xb1l:2026</div><div>Periyot:2</div>
<table class="financial-header-table"><tr><td>Sunum Para Birimi</td><td>1.000 TL</td></tr><tr><td>Finansal Tablo Niteli\xc4\x9fi</td><td>Konsolide</td></tr></table>
<table class="financial-table"><tr><td></td><td class="context-header">Cari D\xc3\xb6nem<br>30.06.2026</td><td class="context-header">\xc3\x96nceki D\xc3\xb6nem<br>31.12.2025</td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>Finansal Durum Tablosu (Bilan\xc3\xa7o)</td></tr></table></td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>Nakit ve Nakit Benzerleri</td></tr></table></td><td class="taxonomy-footnote-cell">5</td><td class="taxonomy-context-value"><div title="195840940">195.840.940</div></td><td class="taxonomy-context-value"><div title="126280395">126.280.395</div></td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>TOPLAM VARLIKLAR</td></tr></table></td><td></td><td class="taxonomy-context-value"><div title="859987516">859.987.516</div></td><td class="taxonomy-context-value"><div title="697096555">697.096.555</div></td></tr>
</table>
<table class="financial-table"><tr><td></td><td class="context-header">Cari D\xc3\xb6nem<br>01.01.2026 - 30.06.2026</td><td class="context-header">\xc3\x96nceki D\xc3\xb6nem<br>01.01.2025 - 30.06.2025</td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>Kar veya Zarar Tablosu</td></tr></table></td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>Has\xc4\xb1lat</td></tr></table></td><td>20</td><td class="taxonomy-context-value"><div title="662788010">662.788.010</div></td><td class="taxonomy-context-value"><div title="464119398">464.119.398</div></td></tr>
</table></body></html>'''


def test_fin001_identity_and_core_values():
    result = import_kap_financial_xls_bytes(SAMPLE, source_name="TUPRS_1643116_2026_2.xls")
    assert result.identity.symbol == "TUPRS"
    assert result.identity.disclosure_id == "1643116"
    assert result.identity.fiscal_year == 2026
    assert result.identity.fiscal_period == 2
    assert result.identity.currency == "TRY"
    assert result.identity.currency_scale == Decimal("1000")
    assert result.identity.consolidation_scope == "KONSOLIDE"
    current = result.current_values()
    assert current["CASH_EQUIVALENTS"] == Decimal("195840940")
    assert current["TOTAL_ASSETS"] == Decimal("859987516")
    assert current["REVENUE"] == Decimal("662788010")
