from pathlib import Path


def test_dashboard_deneme_portfoyunu_icerir() -> None:
    source = Path("backend/app/ui/prebreakout_dashboard.py").read_text(encoding="utf-8")
    assert 'st.subheader("Deneme Portföyü")' in source
    assert "deneme_islemini_hesapla(" in source
    assert "deneme_portfoyu_ozeti(" in source
    assert '"Deneme portföyünü CSV indir"' in source
    assert "Gerçek emir gönderilmez" in source
