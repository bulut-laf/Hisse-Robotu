from pathlib import Path

UI = Path("backend/app/ui/news_center_dashboard.py")


def _source() -> str:
    return UI.read_text(encoding="utf-8")


def test_sprint153_impact_motoru_uiya_baglanir():
    source = _source()
    assert "from backend.app.news_center.impact import assess_event_impact, impact_rows" in source
    assert '"Etki Bağlantıları"' in source
    assert "Deterministik etki bağlantıları" in source


def test_etki_ekrani_fiyat_yonu_tahmini_olmadigini_aciklar():
    source = _source().casefold()
    assert "fiyat yönü tahmini değildir" in source
    assert "sistem sektör veya hisse uydurmadı" in source


def test_sprint153_teknik_karar_motoruna_baglanti_eklemez():
    source = _source().casefold()
    forbidden = (
        "technical_score =",
        "buy_signal",
        "sell_signal",
        "signal_engine",
        "risk_engine",
    )
    for token in forbidden:
        assert token not in source
