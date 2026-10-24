from pathlib import Path

UI = Path("backend/app/ui/news_center_dashboard.py")


def source() -> str:
    return UI.read_text(encoding="utf-8-sig")


def test_portfoy_etki_radari_v11_rolu_aciktir():
    text = source()
    assert "PORTFOY_ETKI_RADARI_V11_ROLE_CLARITY" in text
    assert "Portföy Etki Radarı — Açık Pozisyon Haber/Olay Etkisi" in text
    assert "Haber/Olay → Etki Bağlantıları / Sektör Etki Haritası → Açık Gölge Pozisyonu → Portföy Etki Radarı" in text
    assert "Radar fiyat yönü tahmini, AL/SAT kararı, teknik skor veya yeni pozisyon üretmez" in text


def test_portfoy_etki_radari_v11_mevcut_kontratlari_korur():
    text = source()
    expected = (
        '"Portföy Etki Radarı"',
        "ShadowPortfolioStore",
        "OPEN_STATUS",
        "build_portfolio_impact_radar",
        "portfolio_symbol_summary_rows",
        "portfolio_impact_rows",
        "Doğrudan hisse eşleşmesi",
        "Önem ≥80 olay",
        "DIRECT_SYMBOL > SECTOR > ",
        "MARKET. Bu öncelik yalnız bağlantı gücünü seçer; fiyat ",
        "yönü üretmez.",
        "Gerekçe",
    )
    for item in expected:
        assert item in text
