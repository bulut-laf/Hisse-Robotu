from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from backend.app.news_center.importance import calculate_importance
from backend.app.news_center.models import (
    EventType,
    MarketScope,
    SourceTier,
)


TZ = ZoneInfo("Europe/Istanbul")


def test_resmi_makro_olay_yuksek_ve_deterministik_skor_alir():
    occurred = datetime(2026, 8, 5, 10, 0, tzinfo=TZ)
    first = calculate_importance(
        source_tier=SourceTier.TIER_1_OFFICIAL,
        market_scope=MarketScope.TURKEY_MACRO,
        event_type=EventType.PARA_POLITIKASI,
        occurred_at=occurred,
        published_at=occurred + timedelta(minutes=20),
    )
    second = calculate_importance(
        source_tier=SourceTier.TIER_1_OFFICIAL,
        market_scope=MarketScope.TURKEY_MACRO,
        event_type=EventType.PARA_POLITIKASI,
        occurred_at=occurred,
        published_at=occurred + timedelta(minutes=20),
    )
    assert first == second
    assert first.total == 99


def test_gec_yayimlanan_diger_haber_daha_dusuk_zaman_puani_alir():
    occurred = datetime(2026, 8, 1, 10, 0, tzinfo=TZ)
    score = calculate_importance(
        source_tier=SourceTier.MANUAL,
        market_scope=MarketScope.OTHER,
        event_type=EventType.DIGER,
        occurred_at=occurred,
        published_at=occurred + timedelta(days=4),
    )
    assert score.time_sensitivity == 3
    assert score.total == 27


def test_ai_ve_teknik_skor_girdisi_yoktur():
    parameters = calculate_importance.__annotations__
    assert "technical_score" not in parameters
    assert "ai_score" not in parameters
