import ast
from pathlib import Path


DASHBOARD = Path("backend/dashboard.py")


EXPECTED_GROUPED_ORDER = (
    "Güncel Teknik Analiz",
    "Piyasa Rejimi",
    "Tek Hisse",
    "Temel Analiz",
    "BIST Toplu Tarama",
    "Momentum Keşif",
    "Ön Yükseliş Hazırlık",
    "Ön Yükseliş Toplu Doğrulama",
    "Açık Pozisyon İzleme",
    "Çoklu Hisse Portföyü",
    "Gölge Portföy",
    "İşlem Kayıp Analizi",
    "Sinyal Sonuçları",
    "Analiz Geçmişi",
    "Aynı Veri Karşılaştırması",
    "Başarı Karşılaştırması",
    "Gecikmeli Veri Pilotu",
    "Günlük Operasyon Paneli",
    "Haftalık Performans Raporu",
    "V1.3 Kalibrasyon Kararı",
)


def _analysis_modes() -> tuple[str, ...]:
    tree = ast.parse(DASHBOARD.read_text(encoding="utf-8-sig"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(
                isinstance(target, ast.Name) and target.id == "ANALIZ_MODLARI"
                for target in node.targets
            ):
                value = ast.literal_eval(node.value)
                assert isinstance(value, tuple)
                return value
    raise AssertionError("ANALIZ_MODLARI bulunamadı.")


def test_analiz_modlari_islev_gruplari_icinde_alfabetiktir() -> None:
    assert _analysis_modes() == EXPECTED_GROUPED_ORDER


def test_varsayilan_ekran_tek_hisse_olarak_korunur() -> None:
    source = DASHBOARD.read_text(encoding="utf-8-sig")
    assert 'index=ANALIZ_MODLARI.index("Tek Hisse")' in source
