import ast
from pathlib import Path


DASHBOARD = Path("backend/dashboard.py")


EXPECTED_ALPHABETICAL_ORDER = (
    'Açık Pozisyon İzleme',
    'Analiz Geçmişi',
    'Aynı Veri Karşılaştırması',
    'Başarı Karşılaştırması',
    'BIST Günlük Piyasa',
    'BIST Toplu Tarama',
    'Çoklu Hisse Portföyü',
    'Erste Hungary',
    'Fırsat Radarı',
    'Finansal Zekâ Paneli',
    'Fon Analiz Merkezi',
    'Gecikmeli Veri Pilotu',
    'Gölge Portföy',
    'Güncel Teknik Analiz',
    'Günlük Operasyon Paneli',
    'Haftalık Performans Raporu',
    'İşlem Kayıp Analizi',
    'Momentum Keşif',
    'Ön Yükseliş Hazırlık',
    'Ön Yükseliş Toplu Doğrulama',
    'Piyasa Haber, Olay ve Etki Merkezi',
    'Piyasa Rejimi',
    'Seans Öncesi Bağlam',
    'Sinyal Sonuçları',
    'Tek Hisse',
    'Temel Analiz',
    'V1.3 Kalibrasyon Kararı',
)

EXPECTED_USAGE_FLOW = (
    'Günlük Operasyon',
    'Araştırma',
    'Hisse İnceleme',
    'Karar Terminali',
    'Portföy & Takip',
    'Uluslararası Fonlar',
)


def _literal_assignment(name: str):
    tree = ast.parse(DASHBOARD.read_text(encoding="utf-8-sig"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(
                isinstance(target, ast.Name) and target.id == name
                for target in node.targets
            ):
                return ast.literal_eval(node.value)
    raise AssertionError(f"{name} bulunamadı.")


def test_analiz_modlarinin_tamami_alfabetiktir() -> None:
    assert _literal_assignment("ANALIZ_MODLARI") == EXPECTED_ALPHABETICAL_ORDER


def test_sidebar_kullanim_akisi_ile_baslar() -> None:
    assert _literal_assignment("KULLANIM_AKISI") == EXPECTED_USAGE_FLOW
    source = DASHBOARD.read_text(encoding="utf-8-sig")
    assert '"Kullanım akışı"' in source
    assert "options=KULLANIM_AKISI" in source
    assert "options=ANALIZ_MODLARI" not in source


def test_kullanim_akisi_tum_mevcut_modulleri_kapsar() -> None:
    groups = _literal_assignment("AKIS_MODULLERI")
    covered = {module for modules in groups.values() for module in modules}
    assert covered == set(EXPECTED_ALPHABETICAL_ORDER)
    assert groups["Günlük Operasyon"][0] == "Günlük Operasyon Paneli"
    assert groups["Araştırma"][0] == "Fırsat Radarı"
    assert groups["Hisse İnceleme"][0] == "Tek Hisse"
    assert groups["Karar Terminali"][0] == "Güncel Teknik Analiz"
    assert groups["Portföy & Takip"][0] == "Çoklu Hisse Portföyü"

