from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from backend.app.analysis.technical_confirmation import (
    KIRILIM_YOK,
    NEGATIF,
    NOTR,
    POZITIF,
    TEYITLI_ASAGI_KIRILIM,
    TEYITLI_YUKARI_KIRILIM,
    EMA_POZITIF_YAPI,
    UZUN_VADE_POZITIF,
    MomentumConfirmation,
    MovingAverageConfirmation,
    MultiTimeframeTechnicalConfirmation,
    TimeframeConfirmationResult,
    TrendlineBreakoutResult,
)
from backend.app.analysis.trade_plan import (
    ISLEM_VAR,
    ISLEM_YOK,
    KOSULLU_ALIM_PLANI,
    ONAYLI_ALIM_PLANI,
    PLAN_OLUSTURULMADI,
    TradePlanError,
    islem_plani_olustur,
    pozisyon_boyutunu_hesapla,
)
from backend.app.data.multi_timeframe_data import (
    GUNLUK,
    HAFTALIK,
    SAATLIK,
    MultiTimeframeDataBundle,
    TimeframeSnapshot,
)


def _veri(kapanis: float = 100.0, bar: int = 260) -> pd.DataFrame:
    indeks = pd.bdate_range("2025-01-02", periods=bar)
    trend = np.linspace(kapanis - 15.0, kapanis, bar)
    dalga = np.sin(np.linspace(0, 12, bar)) * 1.20
    fiyat = trend + dalga
    return pd.DataFrame(
        {
            "Open": fiyat - 0.30,
            "High": fiyat + 1.50,
            "Low": fiyat - 1.50,
            "Close": fiyat,
            "Volume": np.full(bar, 1_000_000.0),
        },
        index=indeks,
    )


def _snapshot(ad: str, veri: pd.DataFrame) -> TimeframeSnapshot:
    interval = {SAATLIK: "1h", GUNLUK: "1d", HAFTALIK: "1wk"}[ad]
    return TimeframeSnapshot(
        ad=ad,
        interval=interval,
        period="test",
        veri=veri,
        tamamlanmamis_bar_cikarildi=False,
        veri_kimligi=f"{ad}-veri",
    )


def _paket(sembol: str = "THYAO.IS", kimlik: str = "paket-1") -> MultiTimeframeDataBundle:
    veri = _veri()
    return MultiTimeframeDataBundle(
        sembol=sembol,
        zaman_dilimleri=(
            _snapshot(SAATLIK, veri.copy()),
            _snapshot(GUNLUK, veri.copy()),
            _snapshot(HAFTALIK, veri.copy()),
        ),
        veri_kimligi=kimlik,
    )


def _kirilim(durum: str = KIRILIM_YOK, hacim: bool = True) -> TrendlineBreakoutResult:
    yukari = durum == TEYITLI_YUKARI_KIRILIM
    asagi = durum == TEYITLI_ASAGI_KIRILIM
    return TrendlineBreakoutResult(
        durum=durum,
        yon=POZITIF if yukari else NEGATIF if asagi else NOTR,
        cizgi_tipi="Direnç" if yukari else "Destek" if asagi else "Yok",
        cizgi_degeri=100.0 if durum != KIRILIM_YOK else None,
        onceki_cizgi_degeri=99.5 if durum != KIRILIM_YOK else None,
        pivot_sayisi=2 if durum != KIRILIM_YOK else 0,
        kapanis_teyidi=yukari or asagi,
        erken_uyari=False,
        hacim_orani=1.80 if hacim else 1.00,
        hacim_teyidi=hacim,
    )


def _ortalamalar(death_cross: bool = False) -> MovingAverageConfirmation:
    return MovingAverageConfirmation(
        ema9=103.0,
        ema21=101.0,
        ema55=98.0,
        sma50=100.0,
        sma200=95.0,
        ema9_21_durumu=EMA_POZITIF_YAPI,
        ema21_55_durumu=EMA_POZITIF_YAPI,
        uzun_vade_durumu=UZUN_VADE_POZITIF,
        golden_cross=False,
        death_cross=death_cross,
    )


def _momentum(yon: str = POZITIF) -> MomentumConfirmation:
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
    skor: int = 80,
    destek: float | None = 96.0,
    direnc: float | None = 112.0,
    kirilim: str = KIRILIM_YOK,
    death_cross: bool = False,
) -> TimeframeConfirmationResult:
    interval = {SAATLIK: "1h", GUNLUK: "1d", HAFTALIK: "1wk"}[ad]
    return TimeframeConfirmationResult(
        ad=ad,
        interval=interval,
        son_zaman=pd.Timestamp("2026-07-24"),
        kapanis=100.0,
        destek=destek,
        direnc=direnc,
        destek_gucu="Güçlü" if destek is not None else None,
        direnc_gucu="Güçlü" if direnc is not None else None,
        kirilim=_kirilim(kirilim),
        ortalamalar=_ortalamalar(death_cross=death_cross),
        momentum=_momentum(yon),
        skor=skor,
        yon=yon,
        pozitif_nedenler=("Test pozitif teyidi",) if yon == POZITIF else (),
        riskler=("Test riski",) if yon == NEGATIF else (),
    )


def _analiz(
    skor: int = 80,
    haftalik_yon: str = POZITIF,
    gunluk_yon: str = POZITIF,
    saatlik_yon: str = POZITIF,
    gunluk_kirilim: str = KIRILIM_YOK,
    saatlik_kirilim: str = KIRILIM_YOK,
    veri_kimligi: str = "paket-1",
) -> MultiTimeframeTechnicalConfirmation:
    return MultiTimeframeTechnicalConfirmation(
        sembol="THYAO.IS",
        veri_kimligi=veri_kimligi,
        analiz_kimligi="analiz-1",
        haftalik=_zaman_sonucu(HAFTALIK, yon=haftalik_yon),
        gunluk=_zaman_sonucu(
            GUNLUK,
            yon=gunluk_yon,
            kirilim=gunluk_kirilim,
        ),
        saatlik=_zaman_sonucu(
            SAATLIK,
            yon=saatlik_yon,
            destek=97.0,
            direnc=108.0,
            kirilim=saatlik_kirilim,
        ),
        teyit_skoru=skor,
        teyit_durumu="Test teyidi",
        pozitif_nedenler=("Ortak pozitif teyit",),
        riskler=(),
    )


def test_pozisyon_boyutu_risk_butcesine_gore_hesaplanir() -> None:
    sonuc = pozisyon_boyutunu_hesapla(
        sermaye=100_000.0,
        giris_fiyati=100.0,
        stop_loss=95.0,
        azami_risk_orani=0.01,
    )

    assert sonuc.risk_butcesi == pytest.approx(1_000.0)
    assert sonuc.risk_bazli_lot == 200
    assert sonuc.lot_sayisi == 200
    assert sonuc.planlanan_risk == pytest.approx(1_000.0)


def test_pozisyon_boyutu_sermaye_ile_sinirlanir() -> None:
    sonuc = pozisyon_boyutunu_hesapla(
        sermaye=1_000.0,
        giris_fiyati=300.0,
        stop_loss=299.0,
        azami_risk_orani=0.10,
    )

    assert sonuc.risk_bazli_lot == 100
    assert sonuc.sermaye_bazli_lot == 3
    assert sonuc.lot_sayisi == 3
    assert sonuc.pozisyon_tutari == pytest.approx(900.0)


@pytest.mark.parametrize(
    "girdiler",
    (
        {"sermaye": 0, "giris_fiyati": 100, "stop_loss": 95},
        {"sermaye": 1000, "giris_fiyati": 0, "stop_loss": 95},
        {"sermaye": 1000, "giris_fiyati": 100, "stop_loss": 100},
        {
            "sermaye": 1000,
            "giris_fiyati": 100,
            "stop_loss": 95,
            "azami_risk_orani": 0,
        },
    ),
)
def test_pozisyon_boyutu_gecersiz_girdileri_reddeder(girdiler: dict) -> None:
    with pytest.raises(ValueError):
        pozisyon_boyutunu_hesapla(**girdiler)


def test_pozitif_teyit_onayli_islem_plani_uretir() -> None:
    plan = islem_plani_olustur(_paket(), _analiz())

    assert plan.karar == ISLEM_VAR
    assert plan.plan_tipi == ONAYLI_ALIM_PLANI
    assert plan.giris_alt < plan.giris_ust
    assert plan.stop_loss < plan.giris_alt
    assert plan.hedef_1 > plan.referans_giris
    assert plan.hedef_2 > plan.hedef_1
    assert plan.risk_odul_2 >= 2.0
    assert plan.pozisyon is not None
    assert plan.pozisyon.lot_sayisi > 0


def test_orta_skor_kosullu_plan_uretir_ama_islem_acmaz() -> None:
    plan = islem_plani_olustur(
        _paket(),
        _analiz(skor=50, saatlik_yon=NOTR),
    )

    assert plan.karar == ISLEM_YOK
    assert plan.plan_tipi == KOSULLU_ALIM_PLANI
    assert plan.giris_alt is not None
    assert plan.pozisyon is not None
    assert plan.beklenen_teyitler


def test_dusuk_skor_islem_plani_olusturmaz() -> None:
    plan = islem_plani_olustur(_paket(), _analiz(skor=25))

    assert plan.karar == ISLEM_YOK
    assert plan.plan_tipi == PLAN_OLUSTURULMADI
    assert plan.giris_alt is None
    assert plan.stop_loss is None
    assert plan.pozisyon is None
    assert plan.izleme_tetik_fiyati is not None


def test_gunluk_negatif_yon_islemi_engeller() -> None:
    plan = islem_plani_olustur(
        _paket(),
        _analiz(gunluk_yon=NEGATIF),
    )

    assert plan.karar == ISLEM_YOK
    assert any("Günlük yön" in not_metni for not_metni in plan.notlar)


def test_haftalik_negatif_trend_islemi_engeller() -> None:
    plan = islem_plani_olustur(
        _paket(),
        _analiz(haftalik_yon=NEGATIF),
    )

    assert plan.karar == ISLEM_YOK
    assert any("Haftalık" in not_metni for not_metni in plan.notlar)


def test_teyitli_asagi_kirilim_islemi_engeller() -> None:
    plan = islem_plani_olustur(
        _paket(),
        _analiz(gunluk_kirilim=TEYITLI_ASAGI_KIRILIM),
    )

    assert plan.karar == ISLEM_YOK
    assert any("aşağı kırılım" in not_metni for not_metni in plan.notlar)


def test_teyitli_yukari_kirilim_giris_kaynagini_belirler() -> None:
    plan = islem_plani_olustur(
        _paket(),
        _analiz(saatlik_kirilim=TEYITLI_YUKARI_KIRILIM),
    )

    assert plan.karar == ISLEM_VAR
    assert plan.giris_kaynagi == "Teyitli yukarı kırılım"


def test_yakin_destek_stop_hesabina_katilir() -> None:
    analiz = _analiz()
    analiz = replace(
        analiz,
        gunluk=replace(analiz.gunluk, destek=99.0),
        saatlik=replace(analiz.saatlik, destek=98.5),
    )
    plan = islem_plani_olustur(_paket(), analiz)

    assert plan.stop_kaynagi == "Yakın destek altı + ATR payı"
    assert plan.stop_loss < 99.0


def test_uzak_destekte_atr_stop_kullanilir() -> None:
    analiz = _analiz()
    analiz = replace(
        analiz,
        gunluk=replace(analiz.gunluk, destek=50.0),
        saatlik=replace(analiz.saatlik, destek=55.0),
        haftalik=replace(analiz.haftalik, destek=45.0),
    )
    plan = islem_plani_olustur(_paket(), analiz)

    assert plan.stop_kaynagi == "1.50 ATR"


def test_uygun_direnc_birinci_hedef_olabilir() -> None:
    analiz = _analiz()
    analiz = replace(
        analiz,
        saatlik=replace(analiz.saatlik, direnc=110.0),
        gunluk=replace(analiz.gunluk, direnc=118.0),
        haftalik=replace(analiz.haftalik, direnc=130.0),
    )
    plan = islem_plani_olustur(_paket(), analiz)

    assert plan.hedef_1_kaynagi in {
        "İlk uygun teknik direnç",
        "1.50R ara hedef",
    }
    assert plan.hedef_2 > plan.hedef_1


def test_plan_kimligi_ayni_girdilerde_kararlidir() -> None:
    paket = _paket()
    analiz = _analiz()

    ilk = islem_plani_olustur(paket, analiz)
    ikinci = islem_plani_olustur(paket, analiz)

    assert ilk.plan_kimligi == ikinci.plan_kimligi


def test_sermaye_degisince_plan_kimligi_ve_lot_degisir() -> None:
    paket = _paket()
    analiz = _analiz()

    kucuk = islem_plani_olustur(paket, analiz, sermaye=50_000.0)
    buyuk = islem_plani_olustur(paket, analiz, sermaye=200_000.0)

    assert kucuk.plan_kimligi != buyuk.plan_kimligi
    assert kucuk.pozisyon is not None
    assert buyuk.pozisyon is not None
    assert buyuk.pozisyon.lot_sayisi > kucuk.pozisyon.lot_sayisi


def test_paket_ve_teknik_teyit_kimligi_eslesmelidir() -> None:
    with pytest.raises(TradePlanError, match="veri kimliği"):
        islem_plani_olustur(
            _paket(kimlik="paket-1"),
            _analiz(veri_kimligi="paket-2"),
        )


def test_terminal_calistiricisi_dogrudan_dosya_olarak_acilir() -> None:
    proje_koku = Path(__file__).resolve().parents[2]
    komut_dosyasi = proje_koku / "backend" / "run_trade_plan.py"

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
    assert "sembol" in sonuc.stdout
    assert "--sermaye" in sonuc.stdout
