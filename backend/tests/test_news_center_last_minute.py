from datetime import datetime, timedelta
import hashlib
from zoneinfo import ZoneInfo

import pytest

from backend.app.news_center.last_minute import (
    build_last_minute_feed,
    last_minute_available_sources,
    last_minute_available_symbols,
    last_minute_rows,
)
from backend.app.news_center.models import (
    EventType,
    ImportanceBreakdown,
    MarketEvent,
    MarketScope,
    NewsRecord,
    SourceTier,
)


IST = ZoneInfo("Europe/Istanbul")
NOW = datetime(2026, 8, 5, 18, 0, tzinfo=IST)


def breakdown(score):
    remaining = int(score)
    source = min(30, remaining)
    remaining -= source
    scope = min(25, remaining)
    remaining -= scope
    significance = min(30, remaining)
    remaining -= significance
    time_sensitivity = min(15, remaining)
    return ImportanceBreakdown(
        source_reliability=source,
        market_scope=scope,
        event_significance=significance,
        time_sensitivity=time_sensitivity,
    )


def event(
    event_id,
    *,
    score=80,
    title="Olay",
    symbols=(),
    sectors=(),
):
    return MarketEvent(
        event_id=event_id,
        title=title,
        event_type=EventType.DIGER,
        occurred_at=NOW - timedelta(hours=2),
        market_scope=MarketScope.BIST_WIDE,
        sectors=tuple(sectors),
        symbols=tuple(symbols),
        importance_score=score,
        importance_breakdown=breakdown(score),
    )


def news(
    news_id,
    event_id="E1",
    *,
    published=None,
    archived=None,
    source="Reuters",
    tier=SourceTier.TIER_2_MAJOR_FINANCIAL,
    ref="https://www.reuters.com/markets/example",
    headline=None,
):
    published = published or (NOW - timedelta(minutes=10))
    archived = archived or (published + timedelta(seconds=20))
    return NewsRecord(
        news_id=news_id,
        event_id=event_id,
        source_name=source,
        source_tier=tier,
        headline=headline or f"{news_id} başlık",
        published_at=published,
        body="İçerik",
        source_reference=ref,
        content_hash=hashlib.sha256(news_id.encode()).hexdigest(),
        archived_at=archived,
    )


def test_yayin_zamanina_gore_en_yeni_once():
    brief = build_last_minute_feed(
        (event("E1"),),
        (
            news("N1", published=NOW - timedelta(minutes=20)),
            news("N2", published=NOW - timedelta(minutes=5)),
        ),
        now=NOW,
    )
    assert [item.news_id for item in brief.items] == ["N2", "N1"]


def test_ayni_olaya_iki_kaynak_iki_satir_kalir():
    brief = build_last_minute_feed(
        (event("E1"),),
        (
            news("N1", source="Reuters", ref="https://reuters.com/a"),
            news("N2", source="Bloomberg", ref="https://bloomberg.com/a"),
        ),
        now=NOW,
    )
    assert brief.news_count == 2
    assert brief.unique_event_count == 1


def test_gelecek_zamanli_haber_gosterilmez():
    brief = build_last_minute_feed(
        (event("E1"),),
        (news("N1", published=NOW + timedelta(minutes=1)),),
        now=NOW,
    )
    assert brief.news_count == 0


def test_lookback_eski_haberi_dislar():
    brief = build_last_minute_feed(
        (event("E1"),),
        (news("N1", published=NOW - timedelta(hours=25)),),
        now=NOW,
        lookback_hours=24,
    )
    assert brief.news_count == 0


def test_tum_arsiv_none_ile_mumkun():
    brief = build_last_minute_feed(
        (event("E1"),),
        (news("N1", published=NOW - timedelta(days=30)),),
        now=NOW,
        lookback_hours=None,
    )
    assert brief.news_count == 1


def test_onem_filtresi_mevcut_olay_skorunu_kullanir():
    brief = build_last_minute_feed(
        (event("E1", score=79), event("E2", score=80)),
        (news("N1", "E1"), news("N2", "E2")),
        now=NOW,
        min_importance=80,
    )
    assert [item.news_id for item in brief.items] == ["N2"]


def test_bagli_olay_yoksa_bilgi_uydurulmaz():
    brief = build_last_minute_feed(
        (),
        (news("N1", "E404"),),
        now=NOW,
        min_importance=0,
    )
    item = brief.items[0]
    assert item.event_found is False
    assert item.importance_score is None
    assert item.symbols == ()
    assert item.sectors == ()


def test_bagli_olay_yoksa_onem_filtresinde_gecmez():
    brief = build_last_minute_feed(
        (),
        (news("N1", "E404"),),
        now=NOW,
        min_importance=1,
    )
    assert brief.news_count == 0


def test_kaynak_filtresi_kanonik_ada_gore():
    brief = build_last_minute_feed(
        (event("E1"),),
        (
            news("N1", source="reuters", ref=""),
            news("N2", source="Bloomberg", ref="https://bloomberg.com/a"),
        ),
        now=NOW,
        source_filter="Reuters",
    )
    assert [item.news_id for item in brief.items] == ["N1"]


def test_kaynak_listesi_kanonik_ve_benzersiz():
    sources = last_minute_available_sources(
        (
            news("N1", source="reuters", ref=""),
            news("N2", source="Reuters", ref=""),
            news("N3", source="Bloomberg", ref=""),
        )
    )
    assert sources == ("Bloomberg", "Reuters")


def test_varsayilan_guvenilir_kaynak_filtresi_bilinmeyeni_dislar():
    brief = build_last_minute_feed(
        (event("E1"),),
        (
            news("N1", source="Reuters"),
            news(
                "N2",
                source="Bilinmeyen Site",
                tier=SourceTier.MANUAL,
                ref="https://example.invalid/a",
            ),
        ),
        now=NOW,
    )
    assert [item.news_id for item in brief.items] == ["N1"]


def test_tum_arsiv_seciminde_bilinmeyen_kaynak_gorunebilir():
    brief = build_last_minute_feed(
        (event("E1"),),
        (
            news(
                "N1",
                source="Bilinmeyen Site",
                tier=SourceTier.MANUAL,
                ref="https://example.invalid/a",
            ),
        ),
        now=NOW,
        trusted_only=False,
    )
    assert brief.news_count == 1
    assert brief.items[0].source_is_trusted is False


def test_kap_domaini_dogrulanir():
    brief = build_last_minute_feed(
        (event("E1"),),
        (
            news(
                "N1",
                source="Bilinmeyen",
                tier=SourceTier.MANUAL,
                ref="https://www.kap.org.tr/tr/Bildirim/123",
            ),
        ),
        now=NOW,
    )
    assert brief.kap_news_count == 1
    assert brief.items[0].source_name == "KAP"


def test_hisse_filtresi_yalniz_olay_sembolunden():
    brief = build_last_minute_feed(
        (event("E1", symbols=("THYAO.IS",)),),
        (news("N1"),),
        now=NOW,
        symbol_filter="THYAO",
    )
    assert brief.news_count == 1


def test_haber_basligindan_hisse_tahmini_yapilmaz():
    brief = build_last_minute_feed(
        (event("E1", symbols=()),),
        (news("N1", headline="THYAO güçlü hareket etti"),),
        now=NOW,
        symbol_filter="THYAO",
    )
    assert brief.news_count == 0


def test_hisse_listesi_yalniz_olaylardan_gelir():
    assert last_minute_available_symbols(
        (
            event("E1", symbols=("THYAO.IS", "TUPRS.IS")),
            event("E2", symbols=("THYAO.IS",)),
        )
    ) == ("THYAO.IS", "TUPRS.IS")


def test_portfoy_temasi_dogrudan_sembol_eslesmesidir():
    brief = build_last_minute_feed(
        (event("E1", symbols=("THYAO.IS", "TUPRS.IS")),),
        (news("N1"),),
        now=NOW,
        portfolio_symbols=("THYAO",),
    )
    assert brief.portfolio_news_count == 1
    assert brief.items[0].portfolio_symbols == ("THYAO.IS",)


def test_yalniz_portfoy_filtresi():
    brief = build_last_minute_feed(
        (
            event("E1", symbols=("THYAO.IS",)),
            event("E2", symbols=("ASELS.IS",)),
        ),
        (news("N1", "E1"), news("N2", "E2")),
        now=NOW,
        portfolio_symbols=("THYAO.IS",),
        portfolio_only=True,
    )
    assert [item.news_id for item in brief.items] == ["N1"]


def test_limit_uygulanir():
    brief = build_last_minute_feed(
        (event("E1"),),
        tuple(
            news(
                f"N{i}",
                published=NOW - timedelta(minutes=i),
            )
            for i in range(5)
        ),
        now=NOW,
        limit=2,
    )
    assert brief.news_count == 2


@pytest.mark.parametrize("bad", [0, -1])
def test_gecersiz_lookback_reddedilir(bad):
    with pytest.raises(ValueError, match="lookback_hours"):
        build_last_minute_feed((), (), now=NOW, lookback_hours=bad)


@pytest.mark.parametrize("bad", [-1, 101])
def test_gecersiz_onem_reddedilir(bad):
    with pytest.raises(ValueError, match="min_importance"):
        build_last_minute_feed((), (), now=NOW, min_importance=bad)


@pytest.mark.parametrize("bad", [0, 501])
def test_gecersiz_limit_reddedilir(bad):
    with pytest.raises(ValueError, match="limit"):
        build_last_minute_feed((), (), now=NOW, limit=bad)


def test_saat_dilimsiz_now_reddedilir():
    with pytest.raises(ValueError, match="saat dilimi"):
        build_last_minute_feed(
            (),
            (),
            now=datetime(2026, 8, 5, 18, 0),
        )


def test_satirlar_yeni_skor_uretmez():
    brief = build_last_minute_feed(
        (event("E1", score=88, symbols=("THYAO.IS",)),),
        (news("N1"),),
        now=NOW,
    )
    row = last_minute_rows(brief)[0]
    assert row["Önem"] == 88
    assert "Skor" not in row
    assert "AL/SAT" not in row


def test_birincil_kaynak_sayaci_yalniz_dogrulanmis_kaynaktan():
    brief = build_last_minute_feed(
        (event("E1"),),
        (
            news(
                "N1",
                source="TCMB",
                tier=SourceTier.MANUAL,
                ref="",
            ),
            news(
                "N2",
                source="Bilinmeyen",
                tier=SourceTier.TIER_1_OFFICIAL,
                ref="https://example.invalid",
            ),
        ),
        now=NOW,
        trusted_only=False,
    )
    assert brief.tier1_news_count == 1


def test_son_yayin_zamani_ilk_satirdan_gelir():
    brief = build_last_minute_feed(
        (event("E1"),),
        (
            news("N1", published=NOW - timedelta(minutes=15)),
            news("N2", published=NOW - timedelta(minutes=2)),
        ),
        now=NOW,
    )
    assert brief.latest_published_at == NOW - timedelta(minutes=2)
