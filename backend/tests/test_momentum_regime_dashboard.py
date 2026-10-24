from pathlib import Path


DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard.py"


def test_momentum_rejim_filtresi_arayuzde_gorunur() -> None:
    kaynak = DASHBOARD.read_text(encoding="utf-8")
    assert '"Piyasa rejimi filtresi"' in kaynak
    assert "piyasa_rejimi=(" in kaynak
    assert '"### Rejim bazlı trend filtresi"' in kaynak
    assert '"Rejim nedeniyle elenen"' in kaynak
    assert '"Piyasa rejimi filtresinde elenen hisseler ve nedenleri"' in kaynak


def test_piyasa_rejimi_momentum_oturumuna_aktarilir() -> None:
    kaynak = DASHBOARD.read_text(encoding="utf-8")
    assert 'st.session_state["aktif_piyasa_rejimi"] = ana.rejim' in kaynak
    assert 'st.session_state.get("aktif_piyasa_rejimi")' in kaynak


def test_responsive_piyasa_rejimi_duzeni_korunur() -> None:
    kaynak = DASHBOARD.read_text(encoding="utf-8")
    baslangic = kaynak.index("def piyasa_rejimi_formu()")
    bitis = kaynak.index("def main()", baslangic)
    bolum = kaynak[baslangic:bitis]
    assert "metrik_izgarasi_goster(" in bolum
    assert "for baslangic in range(0, len(bilesenler), 2):" in bolum
    assert 'st.markdown("### Veri güvenliği")' in bolum
