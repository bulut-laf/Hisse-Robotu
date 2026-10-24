from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from backend.app.news_center.economic_calendar import (
    CalendarCategory,
    CalendarImportance,
    DuplicateCalendarEntryError,
    EconomicCalendarStore,
    create_calendar_entry,
)

ISTANBUL = ZoneInfo("Europe/Istanbul")


def _entry(now):
    return create_calendar_entry(
        title="TCMB Para Politikası Kurulu",
        country="Türkiye",
        category=CalendarCategory.CENTRAL_BANK,
        scheduled_at=datetime(2026, 8, 20, 14, 0, tzinfo=ISTANBUL),
        importance=CalendarImportance.CRITICAL,
        previous_value="43%",
        expected_value="42%",
        source_name="TCMB",
        now=now,
    )


def test_store_ayni_news_center_sqlite_icinde_takvim_tablosu_acar(tmp_path):
    store = EconomicCalendarStore(tmp_path / "news_center.sqlite3")
    entry = _entry(datetime(2026, 8, 5, 10, 0, tzinfo=ISTANBUL))
    store.add(entry)
    loaded = store.get(entry.entry_id)
    assert loaded.title == entry.title
    assert loaded.source_name == "TCMB"


def test_ayni_takvim_olayi_duplicate_engellenir(tmp_path):
    store = EconomicCalendarStore(tmp_path / "db.sqlite3")
    first = _entry(datetime(2026, 8, 5, 10, 0, tzinfo=ISTANBUL))
    second = _entry(datetime(2026, 8, 5, 10, 1, tzinfo=ISTANBUL))
    store.add(first)
    with pytest.raises(DuplicateCalendarEntryError):
        store.add(second)


def test_aciklanan_deger_sonradan_guncellenebilir(tmp_path):
    store = EconomicCalendarStore(tmp_path / "db.sqlite3")
    entry = _entry(datetime(2026, 8, 5, 10, 0, tzinfo=ISTANBUL))
    store.add(entry)
    updated = store.update_values(
        entry.entry_id,
        previous_value="43%",
        expected_value="42%",
        actual_value="41,5%",
        notes="Resmî karar yayımlandı.",
    )
    assert updated.actual_value == "41,5%"
    assert updated.notes == "Resmî karar yayımlandı."


def test_gun_listesi_sadece_istenen_gunu_dondurur(tmp_path):
    store = EconomicCalendarStore(tmp_path / "db.sqlite3")
    entry = _entry(datetime(2026, 8, 5, 10, 0, tzinfo=ISTANBUL))
    store.add(entry)
    assert len(store.list_day(entry.scheduled_at.date())) == 1
    assert store.list_day(datetime(2026, 8, 21, tzinfo=ISTANBUL).date()) == ()
