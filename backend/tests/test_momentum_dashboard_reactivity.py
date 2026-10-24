from pathlib import Path


def test_momentum_tarih_kontrolleri_form_disinda_ve_aninda_tepkili() -> None:
    dashboard = Path(__file__).resolve().parents[1] / "dashboard.py"
    kaynak = dashboard.read_text(encoding="utf-8")

    baslangic = kaynak.index('st.header("Momentum keşif")')
    bitis = kaynak.index("    if not calistirildi:", baslangic)
    bolum = kaynak[baslangic:bitis]

    assert 'st.form("momentum_kesif_formu")' not in bolum
    assert 'key="momentum_yeniden_oynat"' in bolum
    assert 'disabled=not yeniden_oynat' in bolum
    assert 'key="momentum_kesim_tarihi"' in bolum
    assert 'st.button(' in bolum
