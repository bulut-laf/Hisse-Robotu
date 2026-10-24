from datetime import date, datetime
import hashlib
from zoneinfo import ZoneInfo

import pytest

from backend.app.news_center.day_end_summary import (
    build_day_end_summary,
    day_end_development_rows,
    day_end_metric_rows,
)
from backend.app.news_center.economic_calendar import (
    CalendarCategory,
    CalendarImportance,
    create_calendar_entry,
)
from backend.app.news_center.models import (
    EventType,
    ImportanceBreakdown,
    MarketEvent,
    MarketScope,
    NewsRecord,
    SourceTier,
)
from backend.app.news_center.portfolio_impact import PortfolioMember


IST = ZoneInfo("Europe/Istanbul")


def dt(day, hour):
    return datetime(2026, 8, day, hour, tzinfo=IST)


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
    day=5,
    hour=10,
    importance=80,
    title="Olay",
    symbols=(),
    sectors=(),
    event_type=EventType.DIGER,
    scope=MarketScope.BIST_WIDE,
):
    return MarketEvent(
        event_id=event_id,
        title=title,
        event_type=event_type,
        market_scope=scope,
        occurred_at=dt(day, hour),
        importance_score=importance,
        importance_breakdown=breakdown(importance),
        sectors=tuple(sectors),
        symbols=tuple(symbols),
        news_ids=(),
    )


def news(
    news_id,
    event_id,
    *,
    day=5,
    hour=11,
    source="Reuters",
    tier=SourceTier.TIER_2_MAJOR_FINANCIAL,
    ref="",
):
    digest = hashlib.sha256(news_id.encode("utf-8")).hexdigest()
    return NewsRecord(
        news_id=news_id,
        event_id=event_id,
        source_name=source,
        source_tier=tier,
        headline=f"{news_id} başlık",
        body="İçerik",
        published_at=dt(day, hour),
        source_reference=ref,
        content_hash=digest,
        archived_at=dt(day, hour),
    )


def calendar(title="TÜFE", *, actual="", importance=CalendarImportance.HIGH):
    return create_calendar_entry(
        title=title,
        country="Türkiye",
        category=CalendarCategory.INFLATION,
        scheduled_at=dt(5, 10),
        importance=importance,
        previous_value="%30",
        expected_value="%31",
        actual_value=actual,
        now=dt(4, 9),
    )


def test_sadece_secili_gunun_olaylarini_sayar():
    summary = build_day_end_summary(
        (event("E1", day=5), event("E2", day=4)),
        (),
        (),
        selected_date=date(2026, 8, 5),
    )
    assert summary.total_event_count == 1


def test_onem_80_esigi_mevcut_olay_skorunu_kullanir():
    summary = build_day_end_summary(
        (event("E1", importance=80), event("E2", importance=79)),
        (),
        (),
        selected_date=date(2026, 8, 5),
    )
    assert summary.high_importance_event_count == 1


def test_gun_ici_haber_sayisi_yayin_tarihine_goredir():
    summary = build_day_end_summary(
        (event("E1"),),
        (news("N1", "E1", day=5), news("N2", "E1", day=4)),
        (),
        selected_date=date(2026, 8, 5),
    )
    assert summary.news_published_count == 1


def test_yalniz_dogrulanmis_kap_kaynaklari_sayilir():
    summary = build_day_end_summary(
        (event("E1"),),
        (
            news("N1", "E1", source="KAP", tier=SourceTier.TIER_1_OFFICIAL),
            news("N2", "E1", source="KAP Haberleri", tier=SourceTier.MANUAL),
        ),
        (),
        selected_date=date(2026, 8, 5),
    )
    assert summary.kap_disclosure_count == 1


def test_kap_org_tr_referansi_dogrulanir():
    summary = build_day_end_summary(
        (event("E1"),),
        (
            news(
                "N1",
                "E1",
                source="Bilinmeyen",
                tier=SourceTier.MANUAL,
                ref="https://www.kap.org.tr/tr/Bildirim/123",
            ),
        ),
        (),
        selected_date=date(2026, 8, 5),
    )
    assert summary.kap_disclosure_count == 1


def test_hisse_olayi_ve_benzersiz_hisse_sayisi():
    summary = build_day_end_summary(
        (
            event("E1", symbols=("THYAO.IS", "TUPRS.IS")),
            event("E2", symbols=("THYAO.IS",)),
            event("E3"),
        ),
        (),
        (),
        selected_date=date(2026, 8, 5),
    )
    assert summary.symbol_event_count == 2
    assert summary.unique_symbol_count == 2


def test_birincil_kaynak_olay_bazinda_bir_kez_sayilir():
    summary = build_day_end_summary(
        (event("E1"),),
        (
            news("N1", "E1", source="KAP", tier=SourceTier.TIER_1_OFFICIAL),
            news("N2", "E1", source="TCMB", tier=SourceTier.TIER_1_OFFICIAL),
        ),
        (),
        selected_date=date(2026, 8, 5),
    )
    assert summary.tier1_event_count == 1


def test_cok_kaynakli_olay_kanonik_kaynak_sayisina_goredir():
    summary = build_day_end_summary(
        (event("E1"),),
        (
            news("N1", "E1", source="Reuters"),
            news("N2", "E1", source="Bloomberg"),
        ),
        (),
        selected_date=date(2026, 8, 5),
    )
    assert summary.multi_source_event_count == 1


def test_ayni_kaynak_iki_haber_cok_kaynak_sayilmaz():
    summary = build_day_end_summary(
        (event("E1"),),
        (
            news("N1", "E1", source="Reuters"),
            news("N2", "E1", source="Reuters"),
        ),
        (),
        selected_date=date(2026, 8, 5),
    )
    assert summary.multi_source_event_count == 0


def test_takvim_sayaclari_ayri_tutulur():
    entries = (
        calendar("TÜFE", actual="%32", importance=CalendarImportance.HIGH),
        calendar("Faiz", actual="", importance=CalendarImportance.CRITICAL),
        calendar("PMI", actual="", importance=CalendarImportance.LOW),
    )
    summary = build_day_end_summary(
        (),
        (),
        entries,
        selected_date=date(2026, 8, 5),
    )
    assert summary.calendar_event_count == 3
    assert summary.calendar_high_critical_count == 2
    assert summary.calendar_announced_count == 1
    assert summary.calendar_waiting_count == 2


def test_portfoy_temasi_mevcut_deterministik_motoru_kullanir():
    summary = build_day_end_summary(
        (
            event(
                "E1",
                symbols=("THYAO.IS",),
                event_type=EventType.KAP_ACIKLAMASI,
                scope=MarketScope.COMPANY,
            ),
        ),
        (news("N1", "E1", source="KAP", tier=SourceTier.TIER_1_OFFICIAL),),
        (),
        selected_date=date(2026, 8, 5),
        portfolio_members=(PortfolioMember("THYAO.IS"),),
    )
    assert summary.affected_portfolio_symbol_count == 1
    assert "THYAO.IS" in summary.affected_portfolio_symbols


def test_portfoy_yoksa_sayaclar_sifirdir():
    summary = build_day_end_summary(
        (event("E1"),),
        (),
        (),
        selected_date=date(2026, 8, 5),
    )
    assert summary.affected_portfolio_symbol_count == 0
    assert summary.direct_portfolio_hit_count == 0


def test_top_developments_mevcut_onem_skoruyla_siralanir():
    summary = build_day_end_summary(
        (
            event("E1", importance=70, title="Düşük"),
            event("E2", importance=90, title="Yüksek"),
        ),
        (),
        (),
        selected_date=date(2026, 8, 5),
    )
    assert [item.event_title for item in summary.top_developments] == ["Yüksek", "Düşük"]


def test_top_limit_uygulanir():
    summary = build_day_end_summary(
        tuple(event(f"E{i}", importance=90-i) for i in range(5)),
        (),
        (),
        selected_date=date(2026, 8, 5),
        top_limit=2,
    )
    assert len(summary.top_developments) == 2


@pytest.mark.parametrize("value", [0, 26, -1])
def test_top_limit_gecersiz_degerleri_reddeder(value):
    with pytest.raises(ValueError, match="top_limit"):
        build_day_end_summary(
            (),
            (),
            (),
            selected_date=date(2026, 8, 5),
            top_limit=value,
        )


def test_saat_dilimsiz_haber_reddedilir():
    bad = news("N1", "E1")
    object.__setattr__(bad, "published_at", datetime(2026, 8, 5, 10))
    with pytest.raises(ValueError, match="saat dilimi"):
        build_day_end_summary(
            (event("E1"),),
            (bad,),
            (),
            selected_date=date(2026, 8, 5),
        )


def test_development_rows_yeni_skor_uretmez():
    summary = build_day_end_summary(
        (event("E1", importance=88),),
        (),
        (),
        selected_date=date(2026, 8, 5),
    )
    rows = day_end_development_rows(summary)
    assert rows[0]["Önem"] == 88
    assert "Skor" not in rows[0]
    assert "AL/SAT" not in rows[0]


def test_metric_rows_bilesenleri_ayri_gosterir():
    summary = build_day_end_summary(
        (event("E1"),),
        (),
        (calendar(),),
        selected_date=date(2026, 8, 5),
    )
    rows = day_end_metric_rows(summary)
    labels = {row["Başlık"] for row in rows}
    assert "Piyasa olayı" in labels
    assert "Takvim olayı" in labels


def test_gecmis_gun_ozeti_sonradan_yayimlanan_haberi_kullanmaz():
    summary = build_day_end_summary(
        (event("E1"),),
        (
            news("N1", "E1", day=5, source="Reuters"),
            news("N2", "E1", day=6, source="Bloomberg"),
        ),
        (),
        selected_date=date(2026, 8, 5),
    )
    assert summary.news_published_count == 1
    assert summary.multi_source_event_count == 0
