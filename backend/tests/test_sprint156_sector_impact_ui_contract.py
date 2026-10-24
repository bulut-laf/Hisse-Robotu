from pathlib import Path

UI = Path("backend/app/ui/news_center_dashboard.py")
MODULE = Path("backend/app/news_center/sector_impact.py")


def _source(path=UI):
    return path.read_text(encoding="utf-8-sig")


def test_sprint156_sektor_haritasi_uiya_baglanir():
    source = _source()
    assert '"Sektör Etki Haritası"' in source
    assert "build_sector_impact_map" in source
    assert "sector_summary_rows" in source
    assert "sector_event_rows" in source


def test_sprint156_donem_filtreleri_var():
    source = _source()
    for label in ("Son 24 saat", "Son 3 gün", "Son 7 gün", "Tüm arşiv"):
        assert label in source


def test_sprint156_yon_tahmini_olmadigini_aciklar():
    source = _source().casefold()
    assert "sektör etki haritası fiyat yönü tahmini değildir" in source
    assert "olumlu/olumsuz fiyat yönü anlamına gelmez" in source


def test_sprint156_teknik_karar_ve_ai_kullanmaz():
    source = _source(MODULE).casefold()
    forbidden = (
        "technical_score",
        "buy_signal",
        "sell_signal",
        "price_direction",
        "gemini",
        "openai",
    )
    for token in forbidden:
        assert token not in source
    assert "ai girdisi" in source
