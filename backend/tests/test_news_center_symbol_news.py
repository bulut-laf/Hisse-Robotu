from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from backend.app.news_center.models import (
    EventType,
    ImportanceBreakdown,
    MarketEvent,
    MarketScope,
    NewsRecord,
    SourceTier,
)
from backend.app.news_center.symbol_news import (
    build_symbol_news_brief,
    symbol_news_available_symbols,
    symbol_news_rows,
)


ISTANBUL = ZoneInfo("Europe/Istanbul")
NOW = datetime(2026, 8, 5, 16, 0, tzinfo=ISTANBUL)


def _breakdown(total: int) -> ImportanceBreakdown:
    source = min(30, total)
    remaining = total - source
    scope = min(25, remaining)
    remaining -= scope
    event = min(30, remaining)
    remaining -= event
    return ImportanceBreakdown(source, scope, event, remaining)


def _event(
    event_id: str,
    *,
    symbols: tuple[str, ...] = ("THYAO",),
    importance: int = 80,
    event_type: EventType = EventType.DIGER,
    occurred_at: datetime | None = None,
) -> MarketEvent:
    return MarketEvent(
        event_id=event_id,
        title=f"Olay {event_id}",
        event_type=event_type,
        occurred_at=occurred_at or (NOW - timedelta(hours=2)),
        market_scope=MarketScope.COMPANY,
        sectors=("Havacılık",),
        symbols=symbols,
        importance_score=importance,
        importance_breakdown=_breakdown(importance),
    )


def _news(
    event_id: str,
    news_id: str,
    *,
    source_name: str = "Reuters",
    source_tier: SourceTier = SourceTier.TIER_2_MAJOR_FINANCIAL,
    source_reference: str = "https://www.reuters.com/world/test",
    published_at: datetime | None = None,
    headline: str | None = None,
) -> NewsRecord:
    stamp = published_at or (NOW - timedelta(minutes=20))
    return NewsRecord(
        news_id=news_id,
        event_id=event_id,
        source_name=source_name,
        source_tier=source_tier,
        headline=headline or f"Haber {news_id}",
        published_at=stamp,
        body="Haber metni.",
        source_reference=source_reference,
        content_hash=(news_id[0] if news_id else "a") * 64,
        archived_at=stamp,
    )


def test_yalniz_acik_olay_sembolleri_hisse_haberine_girer():
    brief = build_symbol_news_brief(
        (_event("e1", symbols=("THYAO",)), _event("e2", symbols=())),
        (_news("e1", "a1"), _news("e2", "b1")),
        now=NOW,
    )
    assert [item.symbol for item in brief.items] == ["THYAO.IS"]


def test_ayni_olay_cok_kaynakta_tek_hisse_satiri_olur():
    brief = build_symbol_news_brief(
        (_event("e1"),),
        (
            _news("e1", "a1", source_name="Reuters"),
            _news(
                "e1",
                "b1",
                source_name="KAP",
                source_tier=SourceTier.TIER_1_OFFICIAL,
                source_reference="https://www.kap.org.tr/tr/Bildirim/1",
            ),
        ),
        now=NOW,
    )
    assert len(brief.items) == 1
    assert brief.items[0].news_count == 2
    assert brief.items[0].source_count == 2


def test_cok_sembollu_olay_her_hisse_icin_bir_satir_olur():
    brief = build_symbol_news_brief(
        (_event("e1", symbols=("THYAO", "TUPRS")),),
        (_news("e1", "a1"),),
        now=NOW,
    )
    assert {item.symbol for item in brief.items} == {"THYAO.IS", "TUPRS.IS"}
    assert brief.unique_event_count == 1
    assert brief.unique_symbol_count == 2


def test_son_yayin_zamani_en_yeni_haberi_kullanir():
    brief = build_symbol_news_brief(
        (_event("e1"),),
        (
            _news("e1", "a1", published_at=NOW - timedelta(hours=3)),
            _news("e1", "b1", published_at=NOW - timedelta(minutes=5), headline="En yeni"),
        ),
        now=NOW,
    )
    item = brief.items[0]
    assert item.latest_published_at == NOW - timedelta(minutes=5)
    assert item.latest_headline == "En yeni"


def test_ana_sira_son_yayin_zamanidir():
    events = (_event("e1", importance=95), _event("e2", symbols=("TUPRS",), importance=60))
    news = (
        _news("e1", "a1", published_at=NOW - timedelta(hours=2)),
        _news("e2", "b1", published_at=NOW - timedelta(minutes=1)),
    )
    brief = build_symbol_news_brief(events, news, now=NOW)
    assert [item.event_id for item in brief.items] == ["e2", "e1"]


def test_lookback_son_yayin_zamanina_gore_calisir():
    brief = build_symbol_news_brief(
        (_event("e1"),),
        (_news("e1", "a1", published_at=NOW - timedelta(hours=25)),),
        now=NOW,
        lookback_hours=24,
    )
    assert brief.items == ()


def test_tum_arsiv_eski_haberi_gosterir():
    brief = build_symbol_news_brief(
        (_event("e1"),),
        (_news("e1", "a1", published_at=NOW - timedelta(days=100)),),
        now=NOW,
        lookback_hours=None,
    )
    assert len(brief.items) == 1


def test_gelecekteki_haber_gosterilmez():
    brief = build_symbol_news_brief(
        (_event("e1"),),
        (_news("e1", "a1", published_at=NOW + timedelta(minutes=1)),),
        now=NOW,
        lookback_hours=None,
    )
    assert brief.items == ()


def test_hisse_filtresi_is_ekini_normalize_eder():
    brief = build_symbol_news_brief(
        (_event("e1", symbols=("THYAO", "TUPRS")),),
        (_news("e1", "a1"),),
        now=NOW,
        symbol_filter="thyao",
    )
    assert [item.symbol for item in brief.items] == ["THYAO.IS"]


def test_onem_filtresi_mevcut_olay_skorunu_kullanir():
    brief = build_symbol_news_brief(
        (_event("e1", importance=79),),
        (_news("e1", "a1"),),
        now=NOW,
        min_importance=80,
    )
    assert brief.items == ()


def test_portfoy_temasi_yalniz_dogrudan_sembol_kesisimidir():
    brief = build_symbol_news_brief(
        (_event("e1", symbols=("THYAO", "TUPRS")),),
        (_news("e1", "a1"),),
        now=NOW,
        portfolio_symbols=("THYAO",),
    )
    flags = {item.symbol: item.is_portfolio_symbol for item in brief.items}
    assert flags == {"THYAO.IS": True, "TUPRS.IS": False}


def test_yalniz_portfoy_filtresi_diger_hisseleri_gizler():
    brief = build_symbol_news_brief(
        (_event("e1", symbols=("THYAO", "TUPRS")),),
        (_news("e1", "a1"),),
        now=NOW,
        portfolio_symbols=("THYAO",),
        portfolio_only=True,
    )
    assert [item.symbol for item in brief.items] == ["THYAO.IS"]


def test_kap_varligi_ayri_bilgi_olarak_gosterilir():
    brief = build_symbol_news_brief(
        (_event("e1"),),
        (
            _news(
                "e1",
                "a1",
                source_name="KAP",
                source_tier=SourceTier.TIER_1_OFFICIAL,
                source_reference="https://www.kap.org.tr/tr/Bildirim/1",
            ),
        ),
        now=NOW,
    )
    assert brief.items[0].kap_news_count == 1
    assert brief.kap_event_count == 1


def test_kap_benzeri_sahte_kaynak_kap_sayilmaz():
    brief = build_symbol_news_brief(
        (_event("e1"),),
        (
            _news(
                "e1",
                "a1",
                source_name="KAP Haber Blog",
                source_tier=SourceTier.OTHER_VERIFIED,
                source_reference="https://example.com/kap.org.tr/1",
            ),
        ),
        now=NOW,
    )
    assert brief.items[0].kap_news_count == 0
    assert brief.kap_event_count == 0


def test_birincil_kaynak_mevcutsa_sayilir():
    brief = build_symbol_news_brief(
        (_event("e1"),),
        (
            _news(
                "e1",
                "a1",
                source_name="Şirket Yatırımcı İlişkileri",
                source_tier=SourceTier.TIER_1_OFFICIAL,
                source_reference="",
            ),
        ),
        now=NOW,
    )
    assert brief.items[0].has_tier1_source is True
    assert brief.tier1_event_count == 1


def test_cok_kaynakli_olay_sayaci_olayi_bir_kez_sayar():
    brief = build_symbol_news_brief(
        (_event("e1", symbols=("THYAO", "TUPRS")),),
        (_news("e1", "a1", source_name="Reuters"), _news("e1", "b1", source_name="Bloomberg", source_reference="https://www.bloomberg.com/x")),
        now=NOW,
    )
    assert brief.multi_source_event_count == 1


def test_yuksek_onem_sayaci_olayi_bir_kez_sayar():
    brief = build_symbol_news_brief(
        (_event("e1", symbols=("THYAO", "TUPRS"), importance=80),),
        (_news("e1", "a1"),),
        now=NOW,
    )
    assert brief.high_importance_event_count == 1


def test_haberi_olmayan_sembollu_olay_hisse_haberi_sayilmaz():
    brief = build_symbol_news_brief((_event("e1"),), (), now=NOW)
    assert brief.items == ()


def test_available_symbols_haber_metninden_tahmin_yapmaz():
    events = (_event("e1", symbols=("THYAO", "TUPRS")), _event("e2", symbols=()))
    assert symbol_news_available_symbols(events) == ("THYAO.IS", "TUPRS.IS")


def test_satirlar_yon_al_sat_ve_yeni_skor_uretmez():
    brief = build_symbol_news_brief(
        (_event("e1", importance=85),),
        (_news("e1", "a1"),),
        now=NOW,
        portfolio_symbols=("THYAO",),
    )
    row = symbol_news_rows(brief)[0]
    assert row["Hisse"] == "THYAO.IS"
    assert row["Önem"] == 85
    assert row["Portföy"] == "Evet"
    assert "Yön" not in row
    assert "AL" not in row
    assert "Skor" not in row


def test_gecersiz_parametreler_reddedilir():
    event = _event("e1")
    news = _news("e1", "a1")
    with pytest.raises(ValueError, match="lookback_hours"):
        build_symbol_news_brief((event,), (news,), now=NOW, lookback_hours=0)
    with pytest.raises(ValueError, match="min_importance"):
        build_symbol_news_brief((event,), (news,), now=NOW, min_importance=101)
    with pytest.raises(ValueError, match="Geçersiz hisse"):
        build_symbol_news_brief((event,), (news,), now=NOW, symbol_filter="!!!")
