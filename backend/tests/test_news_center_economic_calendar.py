from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from backend.app.news_center.economic_calendar import (
    CalendarCategory,
    CalendarImportance,
    EconomicCalendarEntry,
    EconomicCalendarValidationError,
    calendar_rows,
    select_calendar_entries,
)

ISTANBUL = ZoneInfo("Europe/Istanbul")


def _entry(*, importance=CalendarImportance.HIGH, actual="", hour=10):
    return EconomicCalendarEntry(
        entry_id=f"e-{hour}-{importance.value}",
        title="TÜFE",
        country="Türkiye",
        category=CalendarCategory.INFLATION,
        scheduled_at=datetime(2026, 8, 6, hour, 0, tzinfo=ISTANBUL),
        importance=importance,
        previous_value="33,5%",
        expected_value="32,8%",
        actual_value=actual,
    )


def test_naive_tarih_reddedilir():
    with pytest.raises(EconomicCalendarValidationError, match="saat dilimi"):
        EconomicCalendarEntry(
            entry_id="x",
            title="TÜFE",
            country="Türkiye",
            category=CalendarCategory.INFLATION,
            scheduled_at=datetime(2026, 8, 6, 10, 0),
            importance=CalendarImportance.HIGH,
        )


def test_identity_hash_icerikten_deterministik_uretilir():
    a = _entry()
    b = _entry()
    assert a.identity_hash == b.identity_hash
    assert len(a.identity_hash) == 64


def test_asgari_onem_filtresi_calismali():
    entries = (
        _entry(importance=CalendarImportance.LOW, hour=9),
        _entry(importance=CalendarImportance.HIGH, hour=10),
        _entry(importance=CalendarImportance.CRITICAL, hour=11),
    )
    selected = select_calendar_entries(
        entries,
        selected_date=date(2026, 8, 6),
        minimum_importance=CalendarImportance.HIGH,
    )
    assert [item.importance for item in selected] == [
        CalendarImportance.HIGH,
        CalendarImportance.CRITICAL,
    ]


def test_satirlar_yon_yorumu_uretmez():
    rows = calendar_rows(
        (_entry(actual="34,0%"),),
        now=datetime(2026, 8, 6, 12, 0, tzinfo=ISTANBUL),
    )
    assert rows[0]["Açıklanan"] == "34,0%"
    assert rows[0]["Durum"] == "Açıklandı"
    assert "Yön" not in rows[0]
    assert "İyi/Kötü" not in rows[0]


def test_zamani_gecti_actual_yoksa_sonuc_bekleniyor():
    rows = calendar_rows(
        (_entry(actual=""),),
        now=datetime(2026, 8, 6, 12, 0, tzinfo=ISTANBUL),
    )
    assert rows[0]["Durum"] == "Sonuç bekleniyor"
