from datetime import datetime
from decimal import Decimal
from pathlib import Path

from backend.app.analysis.earnings_cash_quality import calculate_earnings_cash_quality
from backend.app.data.historical_financial_series import build_historical_financial_series
from backend.app.data.kap_financial_xls import import_kap_financial_xls_bytes


def _sample_path() -> Path | None:
    candidates = [
        Path("backend/data/fin001_reference/TUPRS_1643116_2026_2.xls"),
        Path("backend/data/TUPRS_1643116_2026_2.xls"),
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


SAMPLE = b'''<html><body>
<h1>TUPRAS TEST A.S.</h1><div>G\xc3\xb6nderim Tarihi:04.08.2026 18:24:32</div><div>Y\xc4\xb1l:2026</div><div>Periyot:2</div>
<table class="financial-header-table"><tr><td>Sunum Para Birimi</td><td>1.000 TL</td></tr><tr><td>Finansal Tablo Niteli\xc4\x9fi</td><td>Konsolide</td></tr></table>
<table class="financial-table"><tr><td></td><td class="context-header">Cari D\xc3\xb6nem<br>01.01.2026 - 30.06.2026</td><td class="context-header">\xc3\x96nceki D\xc3\xb6nem<br>01.01.2025 - 30.06.2025</td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>Kar veya Zarar Tablosu</td></tr></table></td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>Has\xc4\xb1lat</td></tr></table></td><td></td><td class="taxonomy-context-value"><div title="662788010">x</div></td><td class="taxonomy-context-value"><div title="464119398">x</div></td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>BR\xc3\x9cT KAR (ZARAR)</td></tr></table></td><td></td><td class="taxonomy-context-value"><div title="84125684">x</div></td><td class="taxonomy-context-value"><div title="41987994">x</div></td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>ESAS FAAL\xc4\xb0YET KARI (ZARARI)</td></tr></table></td><td></td><td class="taxonomy-context-value"><div title="59025244">x</div></td><td class="taxonomy-context-value"><div title="18160918">x</div></td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>Yat\xc4\xb1r\xc4\xb1m Faaliyetlerinden Giderler</td></tr></table></td><td></td><td class="taxonomy-context-value"><div title="-11217">x</div></td><td class="taxonomy-context-value"><div title="0">x</div></td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>\xc3\x96zkaynak Y\xc3\xb6ntemiyle De\xc4\x9ferlenen Yat\xc4\xb1r\xc4\xb1mlar\xc4\xb1n Karlar\xc4\xb1ndan (Zararlar\xc4\xb1ndan) Paylar</td></tr></table></td><td></td><td class="taxonomy-context-value"><div title="672612">x</div></td><td class="taxonomy-context-value"><div title="747420">x</div></td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>Net Parasal Pozisyon Kazan\xc3\xa7lar\xc4\xb1 (Kay\xc4\xb1plar\xc4\xb1)</td></tr></table></td><td></td><td class="taxonomy-context-value"><div title="-3446844">x</div></td><td class="taxonomy-context-value"><div title="-2571177">x</div></td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>S\xc3\x9cRD\xc3\x9cR\xc3\x9cLEN FAAL\xc4\xb0YETLER VERG\xc4\xb0 \xc3\x96NCES\xc4\xb0 KARI (ZARARI)</td></tr></table></td><td></td><td class="taxonomy-context-value"><div title="61029781">x</div></td><td class="taxonomy-context-value"><div title="18104917">x</div></td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>D\xc3\x96NEM KARI (ZARARI)</td></tr></table></td><td></td><td class="taxonomy-context-value"><div title="50272473">x</div></td><td class="taxonomy-context-value"><div title="11981560">x</div></td></tr>
</table>
<table class="financial-table"><tr><td></td><td class="context-header">Cari D\xc3\xb6nem<br>01.01.2026 - 30.06.2026</td><td class="context-header">\xc3\x96nceki D\xc3\xb6nem<br>01.01.2025 - 30.06.2025</td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>Nakit Ak\xc4\xb1\xc5\x9f Tablosu</td></tr></table></td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>\xc4\xb0\xc5\x9eLETME FAAL\xc4\xb0YETLER\xc4\xb0NDEN NAK\xc4\xb0T AKI\xc5\x9eLARI</td></tr></table></td><td></td><td class="taxonomy-context-value"><div title="132366363">x</div></td><td class="taxonomy-context-value"><div title="15012559">x</div></td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>Maddi ve Maddi Olmayan Duran Varl\xc4\xb1klar\xc4\xb1n Al\xc4\xb1m\xc4\xb1ndan Kaynaklanan Nakit \xc3\x87\xc4\xb1k\xc4\xb1\xc5\x9flar\xc4\xb1</td></tr></table></td><td></td><td class="taxonomy-context-value"><div title="-11858044">x</div></td><td class="taxonomy-context-value"><div title="-10941299">x</div></td></tr>
</table></body></html>'''


def _series():
    imported = import_kap_financial_xls_bytes(SAMPLE, source_name="TUPRS_1643116_2026_2.xls")
    return build_historical_financial_series([imported])


def _metrics(a):
    return {m.code: m.value for m in a.metrics}


def test_fin004_reference_cash_quality_is_cash_backed():
    a = calculate_earnings_cash_quality(_series())
    m = _metrics(a)
    assert a.locked is False
    assert a.score is not None and a.score >= 80
    assert a.cash_quality == "HIGH"
    assert m["OCF_TO_NET_INCOME"] == Decimal("2.63")
    assert m["FREE_CASH_FLOW"] == Decimal("120508319")
    assert m["FCF_MARGIN"] == Decimal("18.18")
    assert "STRONG_CASH_CONVERSION" in a.positive_evidence
    assert "POSITIVE_FCF" in a.positive_evidence


def test_fin004_does_not_fake_normalized_earnings():
    a = calculate_earnings_cash_quality(_series())
    assert a.normalized_earnings_status == "NOT_AVAILABLE_WITHOUT_ONE_OFF_CLASSIFICATION"


def test_fin004_point_in_time_fail_closed():
    a = calculate_earnings_cash_quality(_series(), as_of=datetime(2026, 8, 1, 12, 0, 0))
    assert a.locked is True
    assert a.score is None
    assert a.grade == "DATA_INSUFFICIENT"


def test_fin004_extended_kap_aliases_are_canonical():
    imported = import_kap_financial_xls_bytes(SAMPLE, source_name="TUPRS_1643116_2026_2.xls")
    mapped = {f.metric_code for f in imported.facts if f.metric_code}
    assert {"CAPEX", "MONETARY_GAIN_LOSS", "EQUITY_METHOD_SHARE"}.issubset(mapped)


def test_fin004_not_buy_sell_signal():
    a = calculate_earnings_cash_quality(_series())
    assert "alım/satım sinyali değildir" in a.explanation.casefold()
