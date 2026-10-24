from pathlib import Path


def test_dashboard_surum_hazirligi_bolumunu_icerir() -> None:
    source = Path("backend/app/ui/prebreakout_dashboard.py").read_text(encoding="utf-8")
    assert "on_yukselis_surum_hazirligini_degerlendir(" in source
    assert 'st.subheader("Ön Yükseliş Motoru sürüm hazırlığı")' in source
    assert '"Kullanıma hazır ·' in source
    assert '"Kullanıma hazır değil ·' in source
    assert "varsayılan 10/20 momentum kapısı" in source
