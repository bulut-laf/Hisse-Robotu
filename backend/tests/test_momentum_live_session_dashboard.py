from pathlib import Path


def test_walk_forward_ayrintisinda_guncel_seans_karti_var() -> None:
    dashboard = Path(__file__).resolve().parents[1] / "dashboard.py"
    kaynak = dashboard.read_text(encoding="utf-8")

    assert "Güncel seans karşılaştırması" in kaynak
    assert "Güncel seans verisini getir" in kaynak
    assert "tarihsel aday üretimine" in kaynak
    assert "Canlı seans dâhil azami yükseliş" in kaynak
    assert "guncel_seans_ozeti_getir" in kaynak
