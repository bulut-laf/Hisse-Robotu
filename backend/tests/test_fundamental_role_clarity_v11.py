from pathlib import Path

DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard.py"


def source() -> str:
    return DASHBOARD.read_text(encoding="utf-8")


def test_temel_analiz_v11_rolu_aciktir():
    text = source()

    assert "TEMEL_ANALIZ_V11_ROLE_CLARITY" in text
    assert '"Temel Analiz — Finansal Sağlık ve Kalite İncelemesi"' in text
    assert "bilanço kalitesi, büyüme, kârlılık, borçluluk, likidite ve nakit akışı" in text
    assert "teknik giriş zamanlaması veya AL/SAT kararı üretmez" in text
    assert "Fırsat Radarı aday bulur" in text
    assert "Güncel Teknik Analiz teknik teyidi derinleştirir" in text


def test_temel_analiz_v11_mevcut_kontratlari_korur():
    text = source()

    for expected in (
        "Temel kalite skoru",
        "Toplam kalite skoru",
        "Hasılat",
        "FAVÖK",
        "Net kâr",
        "Özsermaye",
        "ROE",
        "ROA",
        "Cari oran",
        "Borç / özsermaye",
        "Serbest nakit akışı",
        "Temel analiz özet raporu",
        "Temel analiz rapor arşivi",
        "Arşiv arama ve filtreleme",
        "Tazelik kilidi nedeniyle temel oranlar",
    ):
        assert expected in text
