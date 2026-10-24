from backend.app.news_center.classifier import classify_news
from backend.app.news_center.models import EventType, MarketScope, SourceTier


def test_tcmb_politika_faizi_turkiye_makro_olarak_siniflanir():
    result = classify_news(
        source_name="TCMB",
        source_reference="https://www.tcmb.gov.tr/",
        headline="PPK politika faizi kararını açıkladı",
        body="Para Politikası Kurulu politika faizi kararını yayımladı.",
    )
    assert result.source_tier is SourceTier.TIER_1_OFFICIAL
    assert result.event_type is EventType.PARA_POLITIKASI
    assert result.market_scope is MarketScope.TURKEY_MACRO
    assert result.reasons


def test_tuik_enflasyon_haberi_turkiye_makrodur():
    result = classify_news(
        source_name="TÜİK",
        source_reference="",
        headline="TÜFE verileri açıklandı",
        body="Tüketici fiyat endeksi ve enflasyon verileri yayımlandı.",
    )
    assert result.event_type is EventType.ENFLASYON
    assert result.market_scope is MarketScope.TURKEY_MACRO


def test_kap_finansal_sonuc_daha_ozel_olay_turunu_korur():
    result = classify_news(
        source_name="KAP",
        source_reference="https://kap.org.tr/",
        headline="2026 ikinci çeyrek finansal sonuçları",
        body="Şirket bilanço ve net kâr bilgilerini açıkladı.",
    )
    assert result.source_tier is SourceTier.TIER_1_OFFICIAL
    assert result.event_type is EventType.FINANSAL_SONUCLAR
    assert result.market_scope is MarketScope.COMPANY


def test_kap_ozel_kural_yoksa_kap_aciklamasi_olur():
    result = classify_news(
        source_name="KAP",
        source_reference="",
        headline="Şirket açıklaması",
        body="Şirket yeni bir operasyonel gelişme bildirdi.",
    )
    assert result.event_type is EventType.KAP_ACIKLAMASI
    assert result.market_scope is MarketScope.COMPANY


def test_reuters_fed_haberi_global_kapsamdir():
    result = classify_news(
        source_name="Reuters",
        source_reference="https://www.reuters.com/markets/",
        headline="Fed faiz görünümü",
        body="ABD Merkez Bankası faiz patikasına ilişkin değerlendirme yaptı.",
    )
    assert result.source_tier is SourceTier.TIER_2_MAJOR_FINANCIAL
    assert result.event_type is EventType.FAIZ
    assert result.market_scope is MarketScope.GLOBAL


def test_sektor_anahtar_kelimeleri_etki_alani_uretir():
    result = classify_news(
        source_name="Reuters",
        source_reference="",
        headline="Bankacılık ve enerji sektörlerinde görünüm",
        body="Banka hisseleri ile enerji şirketleri gündemde.",
    )
    assert result.sectors == ("Banka", "Enerji")
    assert result.market_scope is MarketScope.SECTOR


def test_bist_endeks_haberi_bist_wide_kapsam_olur():
    result = classify_news(
        source_name="Borsa İstanbul",
        source_reference="",
        headline="BIST 100 endeks duyurusu",
        body="Endeks hesaplamasına ilişkin duyuru yayımlandı.",
    )
    assert result.market_scope is MarketScope.BIST_WIDE


def test_belirsiz_haber_zorla_siniflandirilmaz():
    result = classify_news(
        source_name="Bilinmeyen Kaynak",
        source_reference="",
        headline="Şirketten yeni açıklama",
        body="Genel nitelikte bir açıklama yayımlandı.",
    )
    assert result.source_tier is None
    assert result.event_type is None
    assert result.market_scope is None
    assert result.sectors == ()
    assert result.has_suggestion is False
