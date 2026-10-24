from datetime import datetime
from decimal import Decimal

import pytest

from backend.app.data.historical_financial_series import (
    HistoricalFinancialSeriesError,
    build_historical_financial_series,
    parse_period_label,
)
from backend.app.data.kap_financial_xls import import_kap_financial_xls_bytes


SAMPLE_2026 = b'''<html><body>
<h1>TUPRAS TEST A.S.</h1>
<div>G\xc3\xb6nderim Tarihi:04.08.2026 18:24:32</div>
<div>Y\xc4\xb1l:2026</div><div>Periyot:2</div>
<table class="financial-header-table"><tr><td>Sunum Para Birimi</td><td>1.000 TL</td></tr><tr><td>Finansal Tablo Niteli\xc4\x9fi</td><td>Konsolide</td></tr></table>
<table class="financial-table"><tr><td></td><td class="context-header">Cari D\xc3\xb6nem<br>30.06.2026</td><td class="context-header">\xc3\x96nceki D\xc3\xb6nem<br>31.12.2025</td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>Finansal Durum Tablosu (Bilan\xc3\xa7o)</td></tr></table></td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>Nakit ve Nakit Benzerleri</td></tr></table></td><td></td><td class="taxonomy-context-value"><div title="195840940">195.840.940</div></td><td class="taxonomy-context-value"><div title="126280395">126.280.395</div></td></tr>
</table>
<table class="financial-table"><tr><td></td><td class="context-header">Cari D\xc3\xb6nem<br>01.01.2026 - 30.06.2026</td><td class="context-header">\xc3\x96nceki D\xc3\xb6nem<br>01.01.2025 - 30.06.2025</td><td class="context-header">Cari D\xc3\xb6nem 3 Ayl\xc4\xb1k<br>01.04.2026 - 30.06.2026</td><td class="context-header">\xc3\x96nceki D\xc3\xb6nem 3 Ayl\xc4\xb1k<br>01.04.2025 - 30.06.2025</td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>Kar veya Zarar Tablosu</td></tr></table></td></tr>
<tr><td></td><td class="taxonomy-field-title"><table><tr><td>Has\xc4\xb1lat</td></tr></table></td><td></td><td class="taxonomy-context-value"><div title="662788010">662.788.010</div></td><td class="taxonomy-context-value"><div title="464119398">464.119.398</div></td><td class="taxonomy-context-value"><div title="350000000">350.000.000</div></td><td class="taxonomy-context-value"><div title="240000000">240.000.000</div></td></tr>
</table></body></html>'''


SAMPLE_2025_REVISION = SAMPLE_2026.replace(
    b'G\xc3\xb6nderim Tarihi:04.08.2026 18:24:32',
    b'G\xc3\xb6nderim Tarihi:01.09.2026 09:00:00',
).replace(b'195840940', b'200000000').replace(b'195.840.940', b'200.000.000')


def _import(payload=SAMPLE_2026, name="TUPRS_1643116_2026_2.xls"):
    return import_kap_financial_xls_bytes(payload, source_name=name)


def test_period_semantics_instant_ytd_and_quarter():
    instant = parse_period_label("Cari Dönem 30.06.2026")
    assert instant.kind == "INSTANT"
    assert instant.start_date is None
    assert instant.end_date.isoformat() == "2026-06-30"
    assert instant.comparison_role == "CURRENT_INSTANT"

    ytd = parse_period_label("Cari Dönem 01.01.2026 - 30.06.2026")
    assert ytd.kind == "DURATION"
    assert ytd.start_date.isoformat() == "2026-01-01"
    assert ytd.comparison_role == "CURRENT_YTD"

    q = parse_period_label("Cari Dönem 3 Aylık 01.04.2026 - 30.06.2026")
    assert q.comparison_role == "CURRENT_QUARTER"


def test_fin002_builds_point_in_time_series_without_mixing_semantics():
    series = build_historical_financial_series([_import()])
    assert series.symbol == "TUPRS"
    cash = series.metric_series("CASH_EQUIVALENTS", period_kind="INSTANT")
    assert [p.value for p in cash] == [Decimal("126280395"), Decimal("195840940")]

    revenue = series.metric_series("REVENUE", period_kind="DURATION")
    assert len(revenue) == 4
    assert {p.comparison_role for p in revenue} == {
        "CURRENT_YTD",
        "PRIOR_YEAR_SAME_PERIOD",
        "CURRENT_QUARTER",
        "PRIOR_YEAR_QUARTER",
    }


def test_fin002_latest_revision_wins_and_as_of_remains_point_in_time_safe():
    first = _import()
    revised = _import(SAMPLE_2025_REVISION, "TUPRS_1643117_2026_2.xls")
    series = build_historical_financial_series([first, revised])

    latest = series.latest_value("CASH_EQUIVALENTS", period_kind="INSTANT")
    assert latest is not None
    assert latest.value == Decimal("200000000")
    assert any(w.startswith("REVISED_VALUE:CASH_EQUIVALENTS") for w in series.warnings)

    old_view = series.available_as_of(datetime(2026, 8, 15, 0, 0, 0))
    old = old_view.latest_value("CASH_EQUIVALENTS", period_kind="INSTANT")
    # Point-in-time filtering must expose the original disclosure and must not
    # leak the later revision into an earlier as_of view.
    assert old is not None
    assert old.period_end.isoformat() == "2026-06-30"
    assert old.value == Decimal("195840940")


def test_fin002_rejects_scope_mixing():
    consolidated = _import()
    solo_payload = SAMPLE_2026.replace(b'Konsolide', b'Konsolide Olmayan')
    solo = _import(solo_payload, "TUPRS_1643118_2026_2.xls")
    with pytest.raises(HistoricalFinancialSeriesError, match="Mixed consolidation scopes"):
        build_historical_financial_series([consolidated, solo])
