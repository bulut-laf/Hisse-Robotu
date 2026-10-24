from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from backend.app.news_center.kap_flow import (
    build_kap_flow,
    kap_available_symbols,
    kap_flow_rows,
)
from backend.app.news_center.models import (
    EventType,
    ImportanceBreakdown,
    MarketEvent,
    MarketScope,
    NewsRecord,
    SourceTier,
)


ISTANBUL = ZoneInfo("Europe/Istanbul")
NOW = datetime(2026, 8, 5, 15, 0, tzinfo=ISTANBUL)


def _breakdown(total: int) -> ImportanceBreakdown:
    # Keep components in contract limits while hitting the requested total.
    source = min(30, total)
    remaining = total - source
    scope = min(25, remaining)
    remaining -= scope
    event = min(30, remaining)
    remaining -= event
    time = remaining
    return ImportanceBreakdown(source, scope, event, time)


def _event(
    event_id: str,
    *,
    importance: int = 80,
    symbols: tuple[str, ...] = ("THYAO",),
    event_type: EventType = EventType.KAP_ACIKLAMASI,
) -> MarketEvent:
    return MarketEvent(
        event_id=event_id,
        title=f"Olay {event_id}",
        event_type=event_type,
        occurred_at=NOW - timedelta(hours=1),
        market_scope=MarketScope.COMPANY,
        sectors=(),
        symbols=symbols,
        importance_score=importance,
        importance_breakdown=_breakdown(importance),
    )


def _news(
    event_id: str,
    news_id: str,
    *,
    source_name: str = "KAP",
    source_reference: str = "https://www.kap.org.tr/tr/Bildirim/123",
    published_at: datetime | None = None,
) -> NewsRecord:
    stamp = published_at or (NOW - timedelta(minutes=30))
    return NewsRecord(
        news_id=news_id,
        event_id=event_id,
        source_name=source_name,
        source_tier=SourceTier.TIER_1_OFFICIAL,
        headline=f"Bildirim {news_id}",
        published_at=stamp,
        body="KAP bildirim metni.",
        source_reference=source_reference,
        content_hash=(news_id[0] if news_id else "a") * 64,
        archived_at=stamp,
    )


def test_kap_kaynak_adi_dogrulanmis_bildirimi_alir():
    brief = build_kap_flow(
        (_event("e1"),),
        (_news("e1", "a1", source_reference=""),),
        now=NOW,
    )
    assert brief.total_disclosure_count == 1
    assert brief.disclosures[0].source_match == "source_name"


def test_kap_domaini_kaynak_adi_farkli_olsa_da_alinir():
    brief = build_kap_flow(
        (_event("e1"),),
        (_news("e1", "a1", source_name="Bilinmeyen"),),
        now=NOW,
    )
    assert brief.total_disclosure_count == 1
    assert brief.disclosures[0].source_match == "domain"


def test_kap_benzeri_sahte_kaynak_akisa_alinmaz():
    brief = build_kap_flow(
        (_event("e1"),),
        (
            _news(
                "e1",
                "a1",
                source_name="KAP Haber Blog",
                source_reference="https://example.com/kap.org.tr/Bildirim/1",
            ),
        ),
        now=NOW,
    )
    assert brief.total_disclosure_count == 0


def test_24_saat_disindaki_bildirim_filtrelenir():
    brief = build_kap_flow(
        (_event("e1"),),
        (_news("e1", "a1", published_at=NOW - timedelta(hours=25)),),
        now=NOW,
        lookback_hours=24,
    )
    assert brief.total_disclosure_count == 0


def test_tum_arsiv_seciminde_eski_kap_gosterilir():
    brief = build_kap_flow(
        (_event("e1"),),
        (_news("e1", "a1", published_at=NOW - timedelta(days=40)),),
        now=NOW,
        lookback_hours=None,
    )
    assert brief.total_disclosure_count == 1


def test_gelecekteki_yayin_zamani_gosterilmez():
    brief = build_kap_flow(
        (_event("e1"),),
        (_news("e1", "a1", published_at=NOW + timedelta(minutes=1)),),
        now=NOW,
        lookback_hours=None,
    )
    assert brief.total_disclosure_count == 0


def test_onem_esigi_mevcut_olay_skorunu_kullanir():
    brief = build_kap_flow(
        (_event("e1", importance=70),),
        (_news("e1", "a1"),),
        now=NOW,
        min_importance=80,
    )
    assert brief.total_disclosure_count == 0


def test_hisse_filtresi_is_ekini_normalize_eder():
    events = (_event("e1", symbols=("THYAO",)), _event("e2", symbols=("TUPRS",)))
    news = (_news("e1", "a1"), _news("e2", "b1"))
    brief = build_kap_flow(
        events,
        news,
        now=NOW,
        symbol_filter="thyao",
    )
    assert [item.event_id for item in brief.disclosures] == ["e1"]


def test_portfoy_temasi_yalniz_dogrudan_hisse_kesisimidir():
    brief = build_kap_flow(
        (_event("e1", symbols=("THYAO", "TUPRS")),),
        (_news("e1", "a1"),),
        now=NOW,
        portfolio_symbols=("THYAO", "ASELS"),
    )
    assert brief.disclosures[0].portfolio_symbols == ("THYAO.IS",)
    assert brief.portfolio_touch_count == 1


def test_yalniz_portfoy_filtresi_temasi_olmayan_kapi_gizler():
    brief = build_kap_flow(
        (_event("e1", symbols=("TUPRS",)),),
        (_news("e1", "a1"),),
        now=NOW,
        portfolio_symbols=("THYAO",),
        portfolio_only=True,
    )
    assert brief.total_disclosure_count == 0


def test_sembolsuz_kap_uydurma_hisse_uretmez():
    brief = build_kap_flow(
        (_event("e1", symbols=()),),
        (_news("e1", "a1"),),
        now=NOW,
    )
    assert brief.missing_symbol_count == 1
    assert brief.unique_company_count == 0
    assert brief.disclosures[0].symbols == ()


def test_benzersiz_hisse_sayisi_bildirim_sayisindan_ayridir():
    events = (_event("e1", symbols=("THYAO",)), _event("e2", symbols=("THYAO",)))
    news = (_news("e1", "a1"), _news("e2", "b1"))
    brief = build_kap_flow(events, news, now=NOW)
    assert brief.total_disclosure_count == 2
    assert brief.unique_company_count == 1


def test_akisin_ana_sirasi_en_yeni_yayin_zamanidir():
    events = (_event("e1", importance=90), _event("e2", importance=70))
    news = (
        _news("e1", "a1", published_at=NOW - timedelta(hours=2)),
        _news("e2", "b1", published_at=NOW - timedelta(minutes=5)),
    )
    brief = build_kap_flow(events, news, now=NOW)
    assert [item.event_id for item in brief.disclosures] == ["e2", "e1"]


def test_yuksek_onem_sayaci_80_esigini_kullanir():
    events = (_event("e1", importance=80), _event("e2", importance=79))
    news = (_news("e1", "a1"), _news("e2", "b1"))
    brief = build_kap_flow(events, news, now=NOW)
    assert brief.high_importance_count == 1


def test_olaysiz_kap_girdisi_sessizce_yutulmaz():
    with pytest.raises(ValueError, match="bağlı olay olmadan"):
        build_kap_flow((), (_news("missing", "a1"),), now=NOW)


def test_kap_available_symbols_yalniz_dogrulanmis_kaplardan_gelir():
    events = (_event("e1", symbols=("THYAO",)), _event("e2", symbols=("TUPRS",)))
    news = (
        _news("e1", "a1"),
        _news(
            "e2",
            "b1",
            source_name="KAP Haber Blog",
            source_reference="https://example.com",
        ),
    )
    assert kap_available_symbols(events, news) == ("THYAO.IS",)


def test_satirlar_yon_ve_al_sat_uretmeden_kap_bilgilerini_gosterir():
    brief = build_kap_flow(
        (_event("e1", symbols=("THYAO",), importance=85),),
        (_news("e1", "a1"),),
        now=NOW,
        portfolio_symbols=("THYAO",),
    )
    row = kap_flow_rows(brief)[0]
    assert row["Hisse"] == "THYAO.IS"
    assert row["Portföy teması"] == "THYAO.IS"
    assert row["Önem"] == 85
    assert "AL" not in row
    assert "Yön" not in row


def test_gecersiz_parametreler_reddedilir():
    event = _event("e1")
    news = _news("e1", "a1")
    with pytest.raises(ValueError, match="lookback_hours"):
        build_kap_flow((event,), (news,), now=NOW, lookback_hours=0)
    with pytest.raises(ValueError, match="min_importance"):
        build_kap_flow((event,), (news,), now=NOW, min_importance=101)
