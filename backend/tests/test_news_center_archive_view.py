from datetime import date, datetime, timedelta
import hashlib
from zoneinfo import ZoneInfo

import pytest

from backend.app.news_center.archive_view import (
    archive_available_sectors,
    archive_available_sources,
    archive_available_symbols,
    archive_news_rows,
    build_archive_news_view,
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
BASE = datetime(2026, 8, 5, 12, 0, tzinfo=IST)


def breakdown(score):
    remaining = score
    a = min(30, remaining); remaining -= a
    b = min(25, remaining); remaining -= b
    c = min(30, remaining); remaining -= c
    d = min(15, remaining)
    return ImportanceBreakdown(a, b, c, d)


def event(
    event_id="E1",
    *,
    score=80,
    event_type=EventType.DIGER,
    scope=MarketScope.BIST_WIDE,
    symbols=(),
    sectors=(),
    title="Piyasa olayı",
):
    return MarketEvent(
        event_id=event_id,
        title=title,
        event_type=event_type,
        occurred_at=BASE,
        market_scope=scope,
        sectors=tuple(sectors),
        symbols=tuple(symbols),
        importance_score=score,
        importance_breakdown=breakdown(score),
    )


def news(
    news_id="N1",
    event_id="E1",
    *,
    published=BASE,
    source="Reuters",
    tier=SourceTier.TIER_2_MAJOR_FINANCIAL,
    ref="https://reuters.com/example",
    headline="Test haberi",
    body="Haber metni",
):
    return NewsRecord(
        news_id=news_id,
        event_id=event_id,
        source_name=source,
        source_tier=tier,
        headline=headline,
        published_at=published,
        body=body,
        source_reference=ref,
        content_hash=hashlib.sha256(news_id.encode()).hexdigest(),
        archived_at=published + timedelta(seconds=10),
    )


def test_tarih_araligi_yayin_tarihine_gore():
    items = (
        news("N1", published=datetime(2026, 8, 4, 23, tzinfo=IST)),
        news("N2", published=datetime(2026, 8, 5, 10, tzinfo=IST)),
        news("N3", published=datetime(2026, 8, 6, 1, tzinfo=IST)),
    )
    view = build_archive_news_view(
        (event(),), items,
        start_date=date(2026, 8, 5),
        end_date=date(2026, 8, 5),
    )
    assert [item.news_id for item in view.items] == ["N2"]


def test_kaynak_filtresi_kanonik_ada_gore():
    view = build_archive_news_view(
        (event(),),
        (
            news("N1", source="reuters", ref=""),
            news("N2", source="Bloomberg", ref="https://bloomberg.com/a"),
        ),
        source_filter="Reuters",
    )
    assert [item.news_id for item in view.items] == ["N1"]


def test_guvenilir_kaynak_filtresi():
    view = build_archive_news_view(
        (event(),),
        (
            news("N1", source="Reuters"),
            news("N2", source="Bilinmeyen", tier=SourceTier.MANUAL, ref=""),
        ),
        trusted_only=True,
    )
    assert [item.news_id for item in view.items] == ["N1"]


def test_hisse_filtresi_yalniz_olaydan():
    view = build_archive_news_view(
        (event(symbols=("THYAO.IS",)),),
        (news(headline="ASELS haberi gibi görünen başlık"),),
        symbol_filter="THYAO",
    )
    assert view.news_count == 1


def test_haber_metninden_hisse_tahmini_yapilmaz():
    view = build_archive_news_view(
        (event(symbols=()),),
        (news(headline="THYAO yükseldi"),),
        symbol_filter="THYAO",
    )
    assert view.news_count == 0


def test_sektor_filtresi_yalniz_olaydan():
    view = build_archive_news_view(
        (event(sectors=("Havacılık",)),),
        (news(),),
        sector_filter="havacılık",
    )
    assert view.news_count == 1


def test_olay_turu_filtresi():
    view = build_archive_news_view(
        (
            event("E1", event_type=EventType.KAP_ACIKLAMASI),
            event("E2", event_type=EventType.ENFLASYON),
        ),
        (news("N1", "E1"), news("N2", "E2")),
        event_type_filter=EventType.KAP_ACIKLAMASI,
    )
    assert [item.news_id for item in view.items] == ["N1"]


def test_kapsam_filtresi():
    view = build_archive_news_view(
        (
            event("E1", scope=MarketScope.COMPANY),
            event("E2", scope=MarketScope.GLOBAL),
        ),
        (news("N1", "E1"), news("N2", "E2")),
        market_scope_filter=MarketScope.COMPANY,
    )
    assert [item.news_id for item in view.items] == ["N1"]


def test_onem_filtresi_mevcut_skoru_kullanir():
    view = build_archive_news_view(
        (event("E1", score=79), event("E2", score=80)),
        (news("N1", "E1"), news("N2", "E2")),
        min_importance=80,
    )
    assert [item.news_id for item in view.items] == ["N2"]


def test_metin_arama_baslikta():
    view = build_archive_news_view(
        (event(),),
        (news(headline="TCMB faiz kararı"),),
        text_query="faiz",
    )
    assert view.news_count == 1


def test_metin_arama_govdede():
    view = build_archive_news_view(
        (event(),),
        (news(body="Şirket yeni yatırım açıkladı"),),
        text_query="yatırım",
    )
    assert view.news_count == 1


def test_metin_arama_olay_basliginda():
    view = build_archive_news_view(
        (event(title="Enflasyon verisi"),),
        (news(headline="Veri açıklandı"),),
        text_query="enflasyon",
    )
    assert view.news_count == 1


def test_bagli_olay_yoksa_filtre_yokken_korunur():
    view = build_archive_news_view(
        (),
        (news(event_id="E404"),),
    )
    assert view.news_count == 1
    assert view.items[0].event_found is False
    assert view.items[0].importance_score is None


def test_bagli_olay_yoksa_olay_filtresinde_dislanir():
    view = build_archive_news_view(
        (),
        (news(event_id="E404"),),
        min_importance=1,
    )
    assert view.news_count == 0


def test_kap_dogrulamasi_kaynak_sozlugunden():
    view = build_archive_news_view(
        (event(),),
        (
            news(
                source="Bilinmeyen",
                tier=SourceTier.MANUAL,
                ref="https://www.kap.org.tr/tr/Bildirim/123",
            ),
        ),
    )
    assert view.kap_news_count == 1
    assert view.items[0].source_name == "KAP"


def test_siralama_en_yeni_once():
    view = build_archive_news_view(
        (event(),),
        (
            news("N1", published=BASE - timedelta(hours=2)),
            news("N2", published=BASE - timedelta(hours=1)),
        ),
    )
    assert [item.news_id for item in view.items] == ["N2", "N1"]


def test_limit_uygulanir():
    view = build_archive_news_view(
        (event(),),
        tuple(news(f"N{i}", published=BASE - timedelta(minutes=i)) for i in range(5)),
        limit=2,
    )
    assert view.news_count == 2


def test_kaynak_listesi_kanonik_benzersiz():
    assert archive_available_sources(
        (
            news("N1", source="Reuters", ref=""),
            news("N2", source="reuters", ref=""),
            news("N3", source="Bloomberg", ref=""),
        )
    ) == ("Bloomberg", "Reuters")


def test_hisse_listesi_olaylardan():
    assert archive_available_symbols(
        (
            event("E1", symbols=("THYAO.IS", "TUPRS.IS")),
            event("E2", symbols=("THYAO.IS",)),
        )
    ) == ("THYAO.IS", "TUPRS.IS")


def test_sektor_listesi_benzersiz_case_insensitive():
    assert archive_available_sectors(
        (
            event("E1", sectors=("Havacılık",)),
            event("E2", sectors=("havacılık", "Enerji")),
        )
    ) == ("Enerji", "Havacılık")


def test_metrikler_filtrelenmis_sonuclardan():
    view = build_archive_news_view(
        (
            event("E1", symbols=("THYAO.IS",)),
            event("E2"),
        ),
        (
            news("N1", "E1", source="KAP", tier=SourceTier.TIER_1_OFFICIAL, ref=""),
            news("N2", "E2", source="Reuters"),
        ),
    )
    assert view.news_count == 2
    assert view.unique_event_count == 2
    assert view.source_count == 2
    assert view.tier1_news_count == 1
    assert view.kap_news_count == 1
    assert view.symbol_linked_count == 1


@pytest.mark.parametrize("bad", [-1, 101])
def test_gecersiz_onem_reddedilir(bad):
    with pytest.raises(ValueError, match="min_importance"):
        build_archive_news_view((), (), min_importance=bad)


@pytest.mark.parametrize("bad", [0, 5001])
def test_gecersiz_limit_reddedilir(bad):
    with pytest.raises(ValueError, match="limit"):
        build_archive_news_view((), (), limit=bad)


def test_gecersiz_tarih_araligi_reddedilir():
    with pytest.raises(ValueError, match="Başlangıç"):
        build_archive_news_view(
            (), (),
            start_date=date(2026, 8, 6),
            end_date=date(2026, 8, 5),
        )


def test_saat_dilimsiz_haber_reddedilir():
    bad = news()
    object.__setattr__(bad, "published_at", datetime(2026, 8, 5, 10))
    with pytest.raises(ValueError, match="saat dilimi"):
        build_archive_news_view((event(),), (bad,))


def test_rows_yeni_skor_uretmez():
    view = build_archive_news_view(
        (event(score=88),),
        (news(),),
    )
    row = archive_news_rows(view)[0]
    assert row["Önem"] == 88
    assert "Skor" not in row
    assert "AL/SAT" not in row
