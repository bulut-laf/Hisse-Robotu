from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from backend.app.analysis.position_monitor import (
    AKTIF,
    CIKIS,
    HEDEF_BEKLENIYOR,
    HEDEF_ULASILDI,
    HEDEF_YAKLASIYOR,
    POZISYONU_KAPAT,
    POZISYONU_TASI,
    RISK,
    STOPU_YAKINDAN_IZLE,
    UYARI,
    YENI_ALIM_YAPMA,
    OpenPosition,
    PositionMonitorError,
    acik_pozisyonu_izle,
)
from backend.app.analysis.technical_confirmation import (
    EMA_POZITIF_YAPI,
    KIRILIM_YOK,
    NEGATIF,
    NOTR,
    POZITIF,
    TEYITLI_ASAGI_KIRILIM,
    UZUN_VADE_POZITIF,
    MomentumConfirmation,
    MovingAverageConfirmation,
    MultiTimeframeTechnicalConfirmation,
    TimeframeConfirmationResult,
    TrendlineBreakoutResult,
)
from backend.run_position_monitor import rapor_metni_olustur
from backend.app.data.multi_timeframe_data import (
    GUNLUK,
    HAFTALIK,
    SAATLIK,
    MultiTimeframeDataBundle,
    TimeframeSnapshot,
)


def _veri(
    son_kapanis: float = 110.0,
    zirve_kapanis: float | None = None,
    zirve_fiyat: float | None = None,
    bar: int = 260,
) -> pd.DataFrame:
    indeks = pd.bdate_range("2025-07-28", periods=bar)
    kapanis = np.linspace(90.0, son_kapanis, bar)
    kapanis += np.sin(np.linspace(0, 18, bar)) * 0.60
    kapanis[-1] = son_kapanis
    if zirve_kapanis is not None:
        kapanis[-2] = zirve_kapanis

    yuksek = kapanis + 0.80
    if zirve_fiyat is not None:
        yuksek[-2] = zirve_fiyat

    return pd.DataFrame(
        {
            "Open": kapanis - 0.20,
            "High": yuksek,
            "Low": kapanis - 0.80,
            "Close": kapanis,
            "Volume": np.linspace(1_000_000, 1_500_000, bar),
        },
        index=indeks,
    )


def _snapshot(ad: str, veri: pd.DataFrame) -> TimeframeSnapshot:
    interval = {SAATLIK: "1h", GUNLUK: "1d", HAFTALIK: "1wk"}[ad]
    return TimeframeSnapshot(
        ad=ad,
        interval=interval,
        period="2y",
        veri=veri,
        tamamlanmamis_bar_cikarildi=False,
        veri_kimligi=f"{ad}-veri",
    )


def _paket(
    son_kapanis: float = 110.0,
    zirve_kapanis: float | None = None,
    zirve_fiyat: float | None = None,
    kimlik: str = "paket-1",
) -> MultiTimeframeDataBundle:
    veri = _veri(son_kapanis, zirve_kapanis, zirve_fiyat)
    return MultiTimeframeDataBundle(
        sembol="THYAO.IS",
        zaman_dilimleri=(
            _snapshot(SAATLIK, veri.copy()),
            _snapshot(GUNLUK, veri.copy()),
            _snapshot(HAFTALIK, veri.copy()),
        ),
        veri_kimligi=kimlik,
    )


def _kirilim(durum: str = KIRILIM_YOK) -> TrendlineBreakoutResult:
    return TrendlineBreakoutResult(
        durum=durum,
        yon=NEGATIF if durum == TEYITLI_ASAGI_KIRILIM else NOTR,
        cizgi_tipi="Destek" if durum == TEYITLI_ASAGI_KIRILIM else "Yok",
        cizgi_degeri=100.0 if durum == TEYITLI_ASAGI_KIRILIM else None,
        onceki_cizgi_degeri=101.0 if durum == TEYITLI_ASAGI_KIRILIM else None,
        pivot_sayisi=2 if durum == TEYITLI_ASAGI_KIRILIM else 0,
        kapanis_teyidi=durum == TEYITLI_ASAGI_KIRILIM,
        erken_uyari=False,
        hacim_orani=1.80,
        hacim_teyidi=True,
    )


def _ortalamalar(death_cross: bool = False) -> MovingAverageConfirmation:
    return MovingAverageConfirmation(
        ema9=110.0,
        ema21=108.0,
        ema55=105.0,
        sma50=106.0,
        sma200=100.0,
        ema9_21_durumu=EMA_POZITIF_YAPI,
        ema21_55_durumu=EMA_POZITIF_YAPI,
        uzun_vade_durumu=UZUN_VADE_POZITIF,
        golden_cross=False,
        death_cross=death_cross,
    )


def _momentum(yon: str) -> MomentumConfirmation:
    return MomentumConfirmation(
        rsi14=58.0 if yon == POZITIF else 42.0,
        macd=2.0 if yon == POZITIF else -2.0,
        macd_sinyal=1.0 if yon == POZITIF else -1.0,
        macd_histogram=1.0 if yon == POZITIF else -1.0,
        histogram_gucleniyor=yon == POZITIF,
        durum=yon,
    )


def _zaman_sonucu(
    ad: str,
    yon: str = POZITIF,
    destek: float | None = 90.0,
    kirilim: str = KIRILIM_YOK,
    death_cross: bool = False,
) -> TimeframeConfirmationResult:
    interval = {SAATLIK: "1h", GUNLUK: "1d", HAFTALIK: "1wk"}[ad]
    return TimeframeConfirmationResult(
        ad=ad,
        interval=interval,
        son_zaman=pd.Timestamp("2026-07-24"),
        kapanis=110.0,
        destek=destek,
        direnc=130.0,
        destek_gucu="Güçlü" if destek is not None else None,
        direnc_gucu="Güçlü",
        kirilim=_kirilim(kirilim),
        ortalamalar=_ortalamalar(death_cross=death_cross),
        momentum=_momentum(yon),
        skor=80 if yon == POZITIF else 20 if yon == NEGATIF else 50,
        yon=yon,
        pozitif_nedenler=("Test pozitif",) if yon == POZITIF else (),
        riskler=("Test riski",) if yon == NEGATIF else (),
    )


def _analiz(
    haftalik_yon: str = POZITIF,
    gunluk_yon: str = POZITIF,
    saatlik_yon: str = POZITIF,
    gunluk_kirilim: str = KIRILIM_YOK,
    gunluk_destek: float | None = 90.0,
    veri_kimligi: str = "paket-1",
) -> MultiTimeframeTechnicalConfirmation:
    return MultiTimeframeTechnicalConfirmation(
        sembol="THYAO.IS",
        veri_kimligi=veri_kimligi,
        analiz_kimligi="analiz-1",
        haftalik=_zaman_sonucu(HAFTALIK, haftalik_yon),
        gunluk=_zaman_sonucu(
            GUNLUK,
            gunluk_yon,
            destek=gunluk_destek,
            kirilim=gunluk_kirilim,
        ),
        saatlik=_zaman_sonucu(SAATLIK, saatlik_yon),
        teyit_skoru=75,
        teyit_durumu="Test teyidi",
        pozitif_nedenler=("Ortak pozitif teyit",),
        riskler=(),
    )


def _pozisyon(**degisiklikler: object) -> OpenPosition:
    girdiler: dict[str, object] = {
        "giris_tarihi": "2026-06-01",
        "giris_fiyati": 100.0,
        "lot_sayisi": 100,
        "ilk_stop": 95.0,
        "hedef_1": 120.0,
        "hedef_2": 130.0,
    }
    girdiler.update(degisiklikler)
    return OpenPosition(**girdiler)


def test_pozitif_yapida_pozisyon_aktif_kalir() -> None:
    sonuc = acik_pozisyonu_izle(_paket(110.0), _pozisyon(), _analiz())

    assert sonuc.durum == AKTIF
    assert sonuc.eylem == POZISYONU_TASI
    assert sonuc.acik_kar_zarar == pytest.approx(1_000.0)
    assert sonuc.r_katsayisi == pytest.approx(2.0)


def test_stop_altindaki_kapanis_cikis_uretir() -> None:
    sonuc = acik_pozisyonu_izle(
        _paket(94.0),
        _pozisyon(),
        _analiz(),
    )

    assert sonuc.durum == CIKIS
    assert sonuc.eylem == POZISYONU_KAPAT
    assert any("stop" in risk.lower() for risk in sonuc.riskler)


def test_ikinci_hedefe_ulasilinca_cikis_uretir() -> None:
    sonuc = acik_pozisyonu_izle(
        _paket(131.0),
        _pozisyon(),
        _analiz(),
    )

    assert sonuc.durum == CIKIS
    assert sonuc.hedef_2.durum == HEDEF_ULASILDI
    assert sonuc.kismi_kar_onerisi is False
    assert sonuc.onerilen_kismi_kar_lotu == 0
    assert any("kapanışıyla" in not_metni for not_metni in sonuc.notlar)


def test_birinci_hedef_kismi_kar_onerisi_uretir() -> None:
    sonuc = acik_pozisyonu_izle(
        _paket(121.0),
        _pozisyon(),
        _analiz(),
    )

    assert sonuc.durum == UYARI
    assert sonuc.eylem == YENI_ALIM_YAPMA
    assert sonuc.kismi_kar_onerisi is True
    assert sonuc.onerilen_kismi_kar_lotu == 50


def test_daha_once_kismi_kar_alindiysa_yeni_oneri_uretmez() -> None:
    sonuc = acik_pozisyonu_izle(
        _paket(121.0),
        _pozisyon(hedef_1_gerceklesti=True),
        _analiz(),
    )

    assert sonuc.kismi_kar_onerisi is False
    assert sonuc.onerilen_kismi_kar_lotu == 0


def test_bir_r_karda_stop_basa_basa_tasinir() -> None:
    sonuc = acik_pozisyonu_izle(
        _paket(105.0),
        _pozisyon(),
        _analiz(),
    )

    assert sonuc.dinamik_stop >= 100.0
    assert sonuc.dinamik_stop >= sonuc.ilk_stop


def test_yuksek_karda_atr_iz_suren_stop_devreye_girer() -> None:
    sonuc = acik_pozisyonu_izle(
        _paket(119.5, zirve_kapanis=120.0),
        _pozisyon(hedef_1=125.0, hedef_2=140.0),
        _analiz(),
    )

    assert sonuc.dinamik_stop > sonuc.giris_fiyati
    assert "ATR" in sonuc.stop_kaynagi or "Kâr koruma" in sonuc.stop_kaynagi


def test_mevcut_stop_asla_asagi_indirilmez() -> None:
    sonuc = acik_pozisyonu_izle(
        _paket(110.0),
        _pozisyon(mevcut_stop=108.0),
        _analiz(),
    )

    assert sonuc.onceki_stop == pytest.approx(108.0)
    assert sonuc.dinamik_stop >= 108.0


def test_gunluk_teyitli_asagi_kirilim_erken_cikis_uretir() -> None:
    sonuc = acik_pozisyonu_izle(
        _paket(110.0),
        _pozisyon(),
        _analiz(gunluk_kirilim=TEYITLI_ASAGI_KIRILIM),
    )

    assert sonuc.durum == CIKIS
    assert any("aşağı kırılım" in risk for risk in sonuc.riskler)


def test_haftalik_ve_gunluk_birlikte_negatifse_cikis_uretir() -> None:
    sonuc = acik_pozisyonu_izle(
        _paket(110.0),
        _pozisyon(),
        _analiz(haftalik_yon=NEGATIF, gunluk_yon=NEGATIF),
    )

    assert sonuc.durum == CIKIS


def test_stopa_yakin_pozisyon_risk_durumuna_girer() -> None:
    sonuc = acik_pozisyonu_izle(
        _paket(96.0),
        _pozisyon(ilk_stop=90.0, mevcut_stop=95.8),
        _analiz(gunluk_destek=None),
    )

    assert sonuc.durum == RISK
    assert sonuc.eylem == STOPU_YAKINDAN_IZLE


def test_gunluk_negatif_yon_risk_durumuna_girer() -> None:
    sonuc = acik_pozisyonu_izle(
        _paket(110.0),
        _pozisyon(),
        _analiz(gunluk_yon=NEGATIF),
    )

    assert sonuc.durum == RISK


def test_saatlik_negatif_yon_uyari_uretir() -> None:
    sonuc = acik_pozisyonu_izle(
        _paket(110.0),
        _pozisyon(),
        _analiz(saatlik_yon=NEGATIF),
    )

    assert sonuc.durum == UYARI
    assert any("Saatlik" in risk for risk in sonuc.riskler)


def test_hedef_ilerlemesi_ulasilan_yaklasan_ve_bekleyen_durumlarini_ayirir() -> None:
    ulasilan = acik_pozisyonu_izle(
        _paket(121.0),
        _pozisyon(),
        _analiz(),
    )
    yaklasan = acik_pozisyonu_izle(
        _paket(119.0),
        _pozisyon(),
        _analiz(),
    )
    bekleyen = acik_pozisyonu_izle(
        _paket(110.0),
        _pozisyon(),
        _analiz(),
    )

    assert ulasilan.hedef_1.durum == HEDEF_ULASILDI
    assert yaklasan.hedef_1.durum == HEDEF_YAKLASIYOR
    assert bekleyen.hedef_1.durum == HEDEF_BEKLENIYOR


@pytest.mark.parametrize(
    "pozisyon",
    (
        _pozisyon(giris_fiyati=0),
        _pozisyon(lot_sayisi=0),
        _pozisyon(ilk_stop=100.0),
        _pozisyon(hedef_1=99.0),
        _pozisyon(hedef_2=119.0),
        _pozisyon(mevcut_stop=94.0),
    ),
)
def test_gecersiz_pozisyon_girdileri_reddedilir(pozisyon: OpenPosition) -> None:
    with pytest.raises(ValueError):
        acik_pozisyonu_izle(_paket(), pozisyon, _analiz())


def test_gelecekteki_giris_tarihi_reddedilir() -> None:
    with pytest.raises(PositionMonitorError, match="Giriş tarihi"):
        acik_pozisyonu_izle(
            _paket(),
            _pozisyon(giris_tarihi="2030-01-01"),
            _analiz(),
        )


def test_paket_ve_analiz_veri_kimligi_eslesmelidir() -> None:
    with pytest.raises(PositionMonitorError, match="veri kimliği"):
        acik_pozisyonu_izle(
            _paket(kimlik="paket-1"),
            _pozisyon(),
            _analiz(veri_kimligi="paket-2"),
        )


def test_izleme_kimligi_ayni_girdilerde_kararlidir() -> None:
    paket = _paket()
    pozisyon = _pozisyon()
    analiz = _analiz()

    ilk = acik_pozisyonu_izle(paket, pozisyon, analiz)
    ikinci = acik_pozisyonu_izle(paket, pozisyon, analiz)

    assert ilk.izleme_kimligi == ikinci.izleme_kimligi


def test_mevcut_stop_degisince_izleme_kimligi_degisir() -> None:
    paket = _paket()
    analiz = _analiz()

    ilk = acik_pozisyonu_izle(paket, _pozisyon(), analiz)
    ikinci = acik_pozisyonu_izle(
        paket,
        _pozisyon(mevcut_stop=98.0),
        analiz,
    )

    assert ilk.izleme_kimligi != ikinci.izleme_kimligi



def test_gun_ici_yuksek_fiyat_hedef_1i_gerceklestirir() -> None:
    sonuc = acik_pozisyonu_izle(
        _paket(110.0, zirve_fiyat=121.0),
        _pozisyon(),
        _analiz(),
    )

    assert sonuc.hedef_1.durum == HEDEF_ULASILDI
    assert sonuc.hedef_1.kalan_fiyat == pytest.approx(0.0)
    assert sonuc.kismi_kar_onerisi is True
    assert sonuc.en_yuksek_fiyat == pytest.approx(121.0)


def test_gun_ici_yuksek_fiyat_hedef_2yi_gerceklestirince_cikis_uretir() -> None:
    sonuc = acik_pozisyonu_izle(
        _paket(110.0, zirve_fiyat=131.0),
        _pozisyon(),
        _analiz(),
    )

    assert sonuc.hedef_2.durum == HEDEF_ULASILDI
    assert sonuc.durum == CIKIS
    assert sonuc.eylem == POZISYONU_KAPAT
    assert sonuc.kismi_kar_onerisi is False
    assert sonuc.onerilen_kismi_kar_lotu == 0
    assert any("gün içi en yüksek" in not_metni for not_metni in sonuc.notlar)




def test_ikinci_hedef_raporunda_tam_cikis_gosterilir() -> None:
    sonuc = acik_pozisyonu_izle(
        _paket(110.0, zirve_fiyat=131.0),
        _pozisyon(),
        _analiz(),
    )

    rapor = rapor_metni_olustur(sonuc)

    assert "Kâr alma değerlendirmesi : Tam çıkış" in rapor
    assert "Kısmi kâr değerlendirmesi" not in rapor

def test_giris_tarihinden_onceki_yuksek_fiyat_hedefi_gerceklestirmez() -> None:
    paket = _paket(110.0)
    gunluk = paket.getir(GUNLUK).veri
    onceki_tarih = gunluk.index[10]
    assert onceki_tarih < pd.Timestamp("2026-06-01")
    gunluk.loc[onceki_tarih, "High"] = 150.0

    sonuc = acik_pozisyonu_izle(paket, _pozisyon(), _analiz())

    assert sonuc.hedef_1.durum == HEDEF_BEKLENIYOR
    assert sonuc.kismi_kar_onerisi is False


def test_rapor_satirlari_hizali_ve_ayri_uretilir() -> None:
    sonuc = acik_pozisyonu_izle(
        _paket(110.0, zirve_fiyat=121.0),
        _pozisyon(),
        _analiz(),
    )

    rapor = rapor_metni_olustur(sonuc)

    assert "Giriş tarihi             : 2026-06-01\nGiriş fiyatı" in rapor
    assert "Pozisyon içi zirve       : 121.00" in rapor
    assert "En yüksek kapanış        :" in rapor
    assert "Hedef 1                  : 120.00 — Ulaşıldı — kalan %0.00" in rapor

def test_terminal_calistiricisi_dogrudan_dosya_olarak_acilir() -> None:
    proje_koku = Path(__file__).resolve().parents[2]
    komut_dosyasi = proje_koku / "backend" / "run_position_monitor.py"

    sonuc = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(komut_dosyasi),
            "--help",
        ],
        cwd=proje_koku,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert sonuc.returncode == 0, sonuc.stderr
    assert "--giris" in sonuc.stdout
    assert "--giris-tarihi" in sonuc.stdout
