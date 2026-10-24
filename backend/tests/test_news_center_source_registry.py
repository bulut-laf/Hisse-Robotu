from backend.app.news_center.models import SourceTier
from backend.app.news_center.source_registry import resolve_source


def test_tcmb_aliasi_birinci_seviye_olarak_cozulur():
    result = resolve_source("Türkiye Cumhuriyet Merkez Bankası")
    assert result is not None
    assert result.canonical_name == "TCMB"
    assert result.tier is SourceTier.TIER_1_OFFICIAL
    assert result.matched_by == "source_name"


def test_kap_domaini_birinci_seviye_olarak_cozulur():
    result = resolve_source("Bilinmeyen", "https://www.kap.org.tr/tr/Bildirim/123")
    assert result is not None
    assert result.canonical_name == "KAP"
    assert result.tier is SourceTier.TIER_1_OFFICIAL
    assert result.matched_by == "domain"


def test_reuters_ikinci_seviyedir():
    result = resolve_source("Reuters")
    assert result is not None
    assert result.tier is SourceTier.TIER_2_MAJOR_FINANCIAL


def test_bloomberg_alt_domaini_eslesir():
    result = resolve_source("", "https://www.bloomberg.com/markets")
    assert result is not None
    assert result.canonical_name == "Bloomberg"


def test_beyaz_listede_olmayan_kaynak_otomatik_guvenilir_sayilmaz():
    assert resolve_source("Reuters Benzeri Blog") is None
    assert resolve_source("Örnek Finans", "https://example.com/reuters") is None


def test_sirket_yatirimci_iliskileri_acik_etiketle_birinci_seviye():
    result = resolve_source("Şirket Yatırımcı İlişkileri")
    assert result is not None
    assert result.tier is SourceTier.TIER_1_OFFICIAL
