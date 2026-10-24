from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOMENTUM = ROOT / "app" / "analysis" / "momentum_discovery.py"
BATCH = ROOT / "app" / "data" / "batch_market_data.py"


def test_tek_referans_on_kontrolu_toplu_indirmeden_once_yapilir() -> None:
    kaynak = MOMENTUM.read_text(encoding="utf-8")

    on_kontrol = kaynak.index("on_veri_sonucu = self._on_tazelik_getirici(")
    erken_donus = kaynak.index("return MomentumDiscoveryResult(", on_kontrol)
    toplu_indirme = kaynak.index(
        "veri_sonucu = self._veri_getirici(",
        erken_donus,
    )

    assert on_kontrol < erken_donus < toplu_indirme
    assert "on_tazelik_kontrolu=True" in kaynak


def test_on_kontrol_kilitliyse_motor_calistirilmaz() -> None:
    kaynak = MOMENTUM.read_text(encoding="utf-8")

    on_kilit = kaynak.index("if on_veri_tazeligi.kilitli:")
    erken_donus = kaynak.index("return MomentumDiscoveryResult(", on_kilit)
    motor = kaynak.index("self._motor.analiz_et(", erken_donus)

    assert on_kilit < erken_donus < motor


def test_referans_getirici_tek_sembol_ve_kucuk_donem_kullanir() -> None:
    kaynak = BATCH.read_text(encoding="utf-8")

    assert "def referans_fiyat_verisi_getir(" in kaynak
    assert "islem_gunu: int = 5" in kaynak
    assert 'indirme_donemi: str = "1mo"' in kaynak
    assert "parca_boyutu=1" in kaynak


def test_ozel_veri_getiricilerinde_on_kontrol_varsayilan_kapanir() -> None:
    kaynak = MOMENTUM.read_text(encoding="utf-8")

    assert "veri_getirici is toplu_fiyat_verisi_getir" in kaynak
    assert "if self._veri_tazeligi_kilidi_aktif:" in kaynak
