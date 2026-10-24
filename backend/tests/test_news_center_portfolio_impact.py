from datetime import datetime
from zoneinfo import ZoneInfo

from backend.app.news_center.models import (
    EventType,
    ImportanceBreakdown,
    MarketEvent,
    MarketScope,
)
from backend.app.news_center.portfolio_impact import (
    PortfolioMatchType,
    PortfolioMember,
    build_portfolio_impact_radar,
)


TZ = ZoneInfo("Europe/Istanbul")


def _event(
    *,
    event_id: str,
    title: str,
    event_type: EventType,
    scope: MarketScope,
    sectors=(),
    symbols=(),
    importance=90,
):
    breakdown = ImportanceBreakdown(30, 25, 20, 15)
    if importance != breakdown.total:
        # Model skor bileşenleriyle birebir eşleşme ister; testte toplamı
        # istenen değere güvenli biçimde dağıt.
        source = min(30, importance)
        remaining = importance - source
        scope_score = min(25, remaining)
        remaining -= scope_score
        significance = min(30, remaining)
        remaining -= significance
        time_score = min(15, remaining)
        breakdown = ImportanceBreakdown(
            source,
            scope_score,
            significance,
            time_score,
        )
    return MarketEvent(
        event_id=event_id,
        title=title,
        event_type=event_type,
        occurred_at=datetime(2026, 8, 5, 10, 0, tzinfo=TZ),
        market_scope=scope,
        sectors=tuple(sectors),
        symbols=tuple(symbols),
        importance_score=breakdown.total,
        importance_breakdown=breakdown,
    )


def test_dogrudan_hisse_eslesmesi_sektor_ve_piyasanin_onune_gecer():
    event = _event(
        event_id="e1",
        title="Faiz kararı GARAN etkisi",
        event_type=EventType.PARA_POLITIKASI,
        scope=MarketScope.TURKEY_MACRO,
        sectors=("Banka",),
        symbols=("GARAN",),
    )
    radar = build_portfolio_impact_radar(
        (event,),
        {},
        (PortfolioMember("GARAN", "Bankacılık"),),
    )
    assert len(radar.hits) == 1
    assert radar.hits[0].match_type is PortfolioMatchType.DIRECT_SYMBOL
    assert radar.hits[0].confidence == 100


def test_faiz_olayi_banka_portfoy_hissesine_sektor_duyarliligi_ile_baglanir():
    event = _event(
        event_id="e2",
        title="TCMB faiz kararı",
        event_type=EventType.FAIZ,
        scope=MarketScope.TURKEY_MACRO,
    )
    radar = build_portfolio_impact_radar(
        (event,),
        {},
        (PortfolioMember("AKBNK", "Banka"),),
    )
    assert len(radar.hits) == 1
    assert radar.hits[0].match_type is PortfolioMatchType.SECTOR
    assert radar.hits[0].confidence == 82


def test_piyasa_geneli_olay_sektor_bilgisi_olmayan_acik_hisseyi_de_kapsar():
    event = _event(
        event_id="e3",
        title="BIST genel düzenleme",
        event_type=EventType.REGULASYON,
        scope=MarketScope.BIST_WIDE,
    )
    radar = build_portfolio_impact_radar(
        (event,),
        {},
        (PortfolioMember("ASELS"),),
    )
    assert radar.hits[0].match_type is PortfolioMatchType.MARKET


def test_ilgisiz_sirket_olayi_baska_portfoy_hissesine_baglanmaz():
    event = _event(
        event_id="e4",
        title="ASELS finansal sonuçları",
        event_type=EventType.FINANSAL_SONUCLAR,
        scope=MarketScope.COMPANY,
        symbols=("ASELS",),
    )
    radar = build_portfolio_impact_radar(
        (event,),
        {},
        (PortfolioMember("THYAO", "Ulaştırma"),),
    )
    assert radar.hits == ()
    assert radar.affected_member_count == 0


def test_ayni_sembol_portfoyde_tekrar_edilse_de_tek_uye_sayilir():
    event = _event(
        event_id="e5",
        title="THYAO açıklaması",
        event_type=EventType.KAP_ACIKLAMASI,
        scope=MarketScope.COMPANY,
        symbols=("THYAO",),
    )
    radar = build_portfolio_impact_radar(
        (event,),
        {},
        (
            PortfolioMember("THYAO", "Ulaştırma"),
            PortfolioMember("THYAO.IS", "Ulaştırma"),
        ),
    )
    assert radar.member_count == 1
    assert len(radar.hits) == 1


def test_yuksek_onemli_olay_sayisi_olay_bazinda_sayilir():
    event = _event(
        event_id="e6",
        title="Piyasa geneli yüksek önem",
        event_type=EventType.JEOPOLITIK,
        scope=MarketScope.GLOBAL,
        importance=90,
    )
    radar = build_portfolio_impact_radar(
        (event,),
        {},
        (PortfolioMember("ASELS"), PortfolioMember("THYAO")),
    )
    assert len(radar.hits) == 2
    assert radar.high_importance_event_count == 1


def test_portfoy_etki_motoru_fiyat_yonu_ve_teknik_skor_uretmez():
    annotations = build_portfolio_impact_radar.__annotations__
    text = " ".join(annotations).casefold()
    assert "technical_score" not in text
    assert "price_direction" not in text
    assert "buy_signal" not in text
