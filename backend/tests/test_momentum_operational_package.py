from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard.py"
MOMENTUM = ROOT / "app" / "analysis" / "momentum_discovery.py"


def test_operasyon_metrikleri_sonuca_eklendi() -> None:
    kaynak = MOMENTUM.read_text(encoding="utf-8")

    for alan in (
        "toplu_tarama_baslatildi",
        "indirilen_sembol_sayisi",
        "analiz_edilen_sembol_sayisi",
        "veri_hatasi_sayisi",
        "toplam_sure_saniye",
    ):
        assert alan in kaynak


def test_durum_asamalari_servisten_bildirilir() -> None:
    kaynak = MOMENTUM.read_text(encoding="utf-8")

    assert "durum_bildirimi: StatusCallback | None = None" in kaynak
    assert "ön tazelik kontrolü yapılıyor" in kaynak
    assert "toplu fiyat verisi indiriliyor" in kaynak
    assert "Momentum motoru çalışıyor" in kaynak
    assert "piyasa rejimi filtresi uygulanıyor" in kaynak


def test_momentum_sonucu_oturumda_korunur_ve_imzalanir() -> None:
    kaynak = DASHBOARD.read_text(encoding="utf-8")

    assert 'MOMENTUM_DISCOVERY_RESULT_KEY = "momentum_kesif_sonucu"' in kaynak
    assert 'MOMENTUM_DISCOVERY_SIGNATURE_KEY = "momentum_kesif_imzasi"' in kaynak
    assert "def momentum_kesif_oturum_imzasi(" in kaynak
    assert "isinstance(kayitli_sonuc, MomentumDiscoveryResult)" in kaynak
    assert "önceki sonuç geçersiz" in kaynak


def test_momentum_csv_disari_aktarimlari_var() -> None:
    kaynak = DASHBOARD.read_text(encoding="utf-8")

    assert "def momentum_disari_aktarim_goster(" in kaynak
    assert "Görünen adayları CSV indir" in kaynak
    assert "Rejimde elenenleri CSV indir" in kaynak
    assert "İzleme dışını CSV indir" in kaynak
    assert "Hataları CSV indir" in kaynak


def test_operasyon_ozeti_arayuzde_gorunur() -> None:
    kaynak = DASHBOARD.read_text(encoding="utf-8")

    assert '"### Tarama operasyon özeti"' in kaynak
    assert '"Ön tazelik kontrolü"' in kaynak
    assert '"Toplu tarama"' in kaynak
    assert '"Toplam süre"' in kaynak
