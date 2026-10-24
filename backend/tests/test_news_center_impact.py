from datetime import datetime
from zoneinfo import ZoneInfo

from backend.app.news_center.impact import (
    ImpactRelation,
    ImpactTag,
    ImpactTargetType,
    assess_event_impact,
)
from backend.app.news_center.models import (
    EventType,
    ImportanceBreakdown,
    MarketEvent,
    MarketScope,
    NewsRecord,
    SourceTier,
)

TZ = ZoneInfo("Europe/Istanbul")


def _event(*, event_type, scope, sectors=(), symbols=(), title="Olay"):
    breakdown = ImportanceBreakdown(30, 24, 20, 15)
    return MarketEvent(
        event_id="event-1",
        title=title,
        event_type=event_type,
        occurred_at=datetime(2026, 8, 5, 10, 0, tzinfo=TZ),
        market_scope=scope,
        sectors=sectors,
        symbols=symbols,
        importance_score=breakdown.total,
        importance_breakdown=breakdown,
    )


def _news(body: str):
    stamp = datetime(2026, 8, 5, 10, 10, tzinfo=TZ)
    return NewsRecord(
        news_id="news-1",
        event_id="event-1",
        source_name="Reuters",
        source_tier=SourceTier.TIER_2_MAJOR_FINANCIAL,
        headline="Emtia gelişmesi",
        published_at=stamp,
        body=body,
        source_reference="https://reuters.com/example",
        content_hash="a" * 64,
        archived_at=stamp,
    )


def _find(assessment, target_type, target):
    return next(
        item
        for item in assessment.links
        if item.target_type is target_type and item.target == target
    )


def test_acik_hisse_ve_sektor_dogrudan_baglanti_olur():
    assessment = assess_event_impact(
        _event(
            event_type=EventType.KAP_ACIKLAMASI,
            scope=MarketScope.COMPANY,
            sectors=("Havacılık",),
            symbols=("THYAO",),
        )
    )
    assert _find(assessment, ImpactTargetType.SYMBOL, "THYAO.IS").relation is ImpactRelation.DIRECT
    assert _find(assessment, ImpactTargetType.SECTOR, "Havacılık").confidence == 100
    assert ImpactTag.COMPANY_SPECIFIC in assessment.tags


def test_para_politikasi_bist_ve_faiz_duyarli_sektorleri_baglar():
    assessment = assess_event_impact(
        _event(
            event_type=EventType.PARA_POLITIKASI,
            scope=MarketScope.TURKEY_MACRO,
        )
    )
    assert _find(assessment, ImpactTargetType.MARKET, "BIST Genel").confidence == 100
    assert _find(assessment, ImpactTargetType.SECTOR, "Banka").relation is ImpactRelation.SENSITIVITY
    assert _find(assessment, ImpactTargetType.SECTOR, "Gayrimenkul").relation is ImpactRelation.SENSITIVITY
    assert ImpactTag.RATE_SENSITIVE in assessment.tags


def test_sirket_kapsaminda_sembol_yoksa_hisse_uydurulmaz():
    assessment = assess_event_impact(
        _event(
            event_type=EventType.KAP_ACIKLAMASI,
            scope=MarketScope.COMPANY,
        )
    )
    assert not any(item.target_type is ImpactTargetType.SYMBOL for item in assessment.links)
    assert any("hisse uydurmadı" in note for note in assessment.notes)


def test_brent_haberi_emtia_duyarli_sektorleri_baglar():
    assessment = assess_event_impact(
        _event(event_type=EventType.EMTIA, scope=MarketScope.GLOBAL),
        (_news("Brent petrol fiyatları yükseldi."),),
    )
    assert _find(assessment, ImpactTargetType.SECTOR, "Enerji").confidence == 86
    assert _find(assessment, ImpactTargetType.SECTOR, "Petrokimya").relation is ImpactRelation.SENSITIVITY
    assert _find(assessment, ImpactTargetType.SECTOR, "Havacılık").relation is ImpactRelation.SENSITIVITY


def test_metal_emtia_haberi_madenciligi_baglar():
    assessment = assess_event_impact(
        _event(event_type=EventType.EMTIA, scope=MarketScope.GLOBAL),
        (_news("Altın ve bakır fiyatları hareketlendi."),),
    )
    assert _find(assessment, ImpactTargetType.SECTOR, "Madencilik").confidence == 86


def test_doviz_olayi_sadece_sektor_duyarliligi_uretir_hisse_uydurmaz():
    assessment = assess_event_impact(
        _event(event_type=EventType.DOVIZ, scope=MarketScope.TURKEY_MACRO)
    )
    assert _find(assessment, ImpactTargetType.SECTOR, "Havacılık").relation is ImpactRelation.SENSITIVITY
    assert not any(item.target_type is ImpactTargetType.SYMBOL for item in assessment.links)
    assert any("net döviz pozisyonu" in note for note in assessment.notes)


def test_acik_sektor_duyarlilik_kuralini_directe_yukseltir():
    assessment = assess_event_impact(
        _event(
            event_type=EventType.PARA_POLITIKASI,
            scope=MarketScope.SECTOR,
            sectors=("Banka",),
        )
    )
    link = _find(assessment, ImpactTargetType.SECTOR, "Banka")
    assert link.relation is ImpactRelation.DIRECT
    assert link.confidence == 100
    assert ImpactTag.RATE_SENSITIVE in link.tags
    assert ImpactTag.SECTOR_SPECIFIC in link.tags


def test_diger_ve_other_olay_guvenli_hedef_yoksa_baglanti_uretmez():
    assessment = assess_event_impact(
        _event(event_type=EventType.DIGER, scope=MarketScope.OTHER)
    )
    assert assessment.links == ()


def test_motor_fiyat_yonu_tahmini_alani_tasimaz():
    assessment = assess_event_impact(
        _event(event_type=EventType.ENFLASYON, scope=MarketScope.TURKEY_MACRO)
    )
    for link in assessment.links:
        assert not hasattr(link, "direction")
        assert not hasattr(link, "price_direction")
