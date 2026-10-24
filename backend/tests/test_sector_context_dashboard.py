from pathlib import Path


DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard.py"


def test_bist_toplu_tarama_sektor_baglamini_aktif_eder():
    source = DASHBOARD.read_text(encoding="utf-8")
    assert "sektor_baglami_aktif=True" in source
    assert '"Sektör skoru"' in source
    assert '"Sektör güveni"' in source


def test_dashboard_sektor_baglaminin_teknik_skoru_degistirmedigini_aciklar():
    source = DASHBOARD.read_text(encoding="utf-8")
    assert "sektör skoru teknik hisse skorunu ve aday filtresini değiştirmez" in source
    assert "Bu bilgi teknik skoru değiştirmez." in source
