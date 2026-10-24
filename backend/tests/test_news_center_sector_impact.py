from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from backend.app.news_center.impact import ImpactRelation, ImpactTag
from backend.app.news_center.models import (
    EventType,
    ImportanceBreakdown,
    MarketEvent,
    MarketScope,
)
from backend.app.news_center.sector_impact import build_sector_impact_map


TZ = ZoneInfo("Europe/Istanbul")
BASE = datetime(2026, 8, 5, 12, 0, tzinfo=TZ)


def _breakdown(total: int) -> ImportanceBreakdown:
    source = min(30, total)
    remaining = total - source
    scope = min(25, remaining)
    remaining -= scope
    significance = min(30, remaining)
    remaining -= significance
    time_score = min(15, remaining)
    return ImportanceBreakdown(source, scope, significance, time_score)


def _event(
    event_id: str,
    *,
    title: str,
    event_type: EventType,
    scope: MarketScope,
    occurred_at: datetime = BASE,
    sectors=(),
    symbols=(),
    importance: int = 90,
) -> MarketEvent:
    breakdown = _breakdown(importance)
    return MarketEvent(
        event_id=event_id,
        title=title,
        event_type=event_type,
        occurred_at=occurred_at,
        market_scope=scope,
        sectors=tuple(sectors),
        symbols=tuple(symbols),
        importance_score=breakdown.total,
        importance_breakdown=breakdown,
    )


def test_faiz_olayi_banka_ve_gayrimenkul_sektorlerini_toplular():
    event = _event(
        "e1",
        title="TCMB faiz kararı",
        event_type=EventType.FAIZ,
        scope=MarketScope.TURKEY_MACRO,
    )
    sector_map = build_sector_impact_map((event,))
    by_sector = {item.sector: item for item in sector_map.summaries}

    assert set(by_sector) >= {"Banka", "Gayrimenkul"}
    assert by_sector["Banka"].sensitivity_event_count == 1
    assert by_sector["Banka"].max_link_confidence == 82
    assert sector_map.event_count == 1


def test_acik_sektor_direct_olarak_sayilir_ve_duyarliligin_onune_gecer():
    event = _event(
        "e2",
        title="Bankacılık düzenlemesi",
        event_type=EventType.FAIZ,
        scope=MarketScope.SECTOR,
        sectors=("Banka",),
    )
    sector_map = build_sector_impact_map((event,))
    bank = next(item for item in sector_map.summaries if item.sector == "Banka")
    bank_hit = next(item for item in sector_map.hits if item.sector == "Banka")

    assert bank.direct_event_count == 1
    assert bank.sensitivity_event_count == 0
    assert bank_hit.relation is ImpactRelation.DIRECT
    assert bank_hit.confidence == 100


def test_yuksek_onem_olay_sayisi_olay_bazinda_tek_sayilir():
    event = _event(
        "e3",
        title="Faiz kararı",
        event_type=EventType.FAIZ,
        scope=MarketScope.TURKEY_MACRO,
        importance=90,
    )
    sector_map = build_sector_impact_map((event,))
    assert sector_map.high_importance_event_count == 1
    assert sector_map.sector_count >= 2


def test_since_filtresi_eski_olaylari_disarida_birakir():
    old = _event(
        "old",
        title="Eski faiz olayı",
        event_type=EventType.FAIZ,
        scope=MarketScope.TURKEY_MACRO,
        occurred_at=BASE - timedelta(days=10),
    )
    recent = _event(
        "new",
        title="Yeni enflasyon olayı",
        event_type=EventType.ENFLASYON,
        scope=MarketScope.TURKEY_MACRO,
        occurred_at=BASE - timedelta(days=1),
    )
    sector_map = build_sector_impact_map(
        (old, recent),
        since=BASE - timedelta(days=7),
    )
    ids = {hit.event_id for hit in sector_map.hits}
    assert "old" not in ids
    assert "new" in ids


def test_since_naive_datetime_reddedilir():
    event = _event(
        "e4",
        title="Faiz",
        event_type=EventType.FAIZ,
        scope=MarketScope.TURKEY_MACRO,
    )
    with pytest.raises(ValueError, match="saat dilimi"):
        build_sector_impact_map((event,), since=datetime(2026, 8, 1))


def test_sadece_hisse_baglantisi_olan_sirket_olayi_sektor_uydurmaz():
    event = _event(
        "e5",
        title="ASELS finansal sonuçları",
        event_type=EventType.FINANSAL_SONUCLAR,
        scope=MarketScope.COMPANY,
        symbols=("ASELS",),
    )
    sector_map = build_sector_impact_map((event,))
    assert sector_map.summaries == ()
    assert sector_map.hits == ()


def test_sektor_haritasi_fiyat_yonu_ve_teknik_skor_uretmez():
    annotations = build_sector_impact_map.__annotations__
    text = " ".join(str(value) for value in annotations.values()).casefold()
    assert "technical_score" not in text
    assert "price_direction" not in text
    assert "buy_signal" not in text
