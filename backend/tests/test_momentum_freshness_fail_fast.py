from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOMENTUM = ROOT / "app" / "analysis" / "momentum_discovery.py"
DASHBOARD = ROOT / "dashboard.py"


def test_eski_veride_momentum_motoru_calistirilmaz() -> None:
    kaynak = MOMENTUM.read_text(encoding="utf-8")

    freshness = kaynak.index(
        "veri_tazeligi = toplu_veri_tazeligini_degerlendir("
    )
    lock = kaynak.index("self._veri_tazeligi_kilidi_aktif", freshness)
    locked_flag = kaynak.index("and veri_tazeligi.kilitli", lock)
    engine = kaynak.index("self._motor.analiz_et(", locked_flag)

    assert freshness < lock < locked_flag < engine
    assert "tum_adaylar: tuple[MomentumCandidate, ...] = ()" in kaynak
    assert "motor_hatalari: tuple[MomentumFailure, ...] = tuple(" in kaynak
    assert "tazelik_hatalari" in kaynak


def test_ozel_veri_getiricide_kilit_varsayilan_olarak_kapanir() -> None:
    kaynak = MOMENTUM.read_text(encoding="utf-8")

    assert "veri_tazeligi_kilidi_aktif: bool | None = None" in kaynak
    assert "veri_getirici is toplu_fiyat_verisi_getir" in kaynak


def test_arayuz_eski_veriyi_tamamlandi_diye_gostermez() -> None:
    kaynak = DASHBOARD.read_text(encoding="utf-8")

    assert (
        'text="Veri tazeliği kilidi nedeniyle tarama durduruldu."'
        in kaynak
    )
    assert (
        "if sonuc.veri_tazeligi is not None "
        "and sonuc.veri_tazeligi.kilitli:"
        in kaynak
    )


def test_guncel_veride_normal_tamamlanma_mesaji_korunur() -> None:
    kaynak = DASHBOARD.read_text(encoding="utf-8")

    assert 'text="Momentum keşfi tamamlandı."' in kaynak