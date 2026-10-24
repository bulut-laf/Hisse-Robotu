from __future__ import annotations

from dataclasses import fields

import pandas as pd
import pytest

from backend.app.backtest.backtest_models import (
    BacktestConfig,
    BacktestSignal,
)
from backend.app.backtest.parameter_sensitivity import (
    ParameterScenario,
    ParameterSensitivityAnalyzer,
    ParameterSensitivityError,
    varsayilan_tek_degisken_senaryolari,
)


GORUNUM = "Pozitif Teknik Görünüm"


def fiyat_verisi_olustur() -> pd.DataFrame:
    kapanislar = [
        100.0,
        102.0,
        104.0,
        101.0,
        98.0,
        103.0,
        107.0,
        110.0,
        108.0,
        112.0,
        116.0,
        119.0,
        117.0,
        121.0,
        124.0,
        122.0,
        126.0,
        130.0,
        128.0,
        132.0,
    ]

    return pd.DataFrame(
        {
            "Open": kapanislar,
            "High": [fiyat + 2.0 for fiyat in kapanislar],
            "Low": [fiyat - 2.0 for fiyat in kapanislar],
            "Close": kapanislar,
            "Volume": [1_000_000.0 for _ in kapanislar],
        },
        index=pd.date_range(
            start="2026-01-01",
            periods=len(kapanislar),
            freq="D",
        ),
    )


def sinyaller_olustur() -> tuple[BacktestSignal, ...]:
    tarihler = pd.date_range(
        start="2026-01-01",
        periods=20,
        freq="D",
    )

    return (
        BacktestSignal(
            sembol="AAA.IS",
            sinyal_tarihi=tarihler[0].date(),
            skor=60,
            teknik_gorunum=GORUNUM,
        ),
        BacktestSignal(
            sembol="AAA.IS",
            sinyal_tarihi=tarihler[5].date(),
            skor=72,
            teknik_gorunum=GORUNUM,
        ),
        BacktestSignal(
            sembol="AAA.IS",
            sinyal_tarihi=tarihler[10].date(),
            skor=68,
            teknik_gorunum=GORUNUM,
        ),
    )


def baz_ayar() -> BacktestConfig:
    return BacktestConfig(
        elde_tutma_gunu=3,
        minimum_skor=50,
        baslangic_sermayesi=100_000.0,
        pozisyon_orani=1.0,
        islem_maliyeti_orani=0.0,
        zarar_durdur_orani=0.05,
        hedef_orani=0.10,
    )


def test_varsayilan_senaryolar_baz_ve_sekiz_varyasyon_uretir() -> None:
    senaryolar = varsayilan_tek_degisken_senaryolari(
        BacktestConfig(
            elde_tutma_gunu=10,
            minimum_skor=50,
            zarar_durdur_orani=0.05,
            hedef_orani=0.10,
        )
    )

    assert len(senaryolar) == 9
    assert senaryolar[0].ad == "Baz"
    assert len({senaryo.ad for senaryo in senaryolar}) == 9


def test_her_varyasyonda_yalnizca_bir_ana_parametre_degisir() -> None:
    baz = BacktestConfig(
        elde_tutma_gunu=10,
        minimum_skor=50,
        zarar_durdur_orani=0.05,
        hedef_orani=0.10,
    )
    senaryolar = varsayilan_tek_degisken_senaryolari(baz)
    ana_alanlar = {
        "elde_tutma_gunu",
        "minimum_skor",
        "zarar_durdur_orani",
        "hedef_orani",
    }

    for senaryo in senaryolar[1:]:
        degisenler = {
            alan.name
            for alan in fields(BacktestConfig)
            if getattr(senaryo.yapilandirma, alan.name)
            != getattr(baz, alan.name)
        }
        assert len(degisenler) == 1
        assert degisenler.issubset(ana_alanlar)


def test_senaryolar_ayni_veri_ve_sinyallerle_karsilastirilir() -> None:
    baz = baz_ayar()
    senaryolar = (
        ParameterScenario("Baz", "Baz ayarlar", baz),
        ParameterScenario(
            "Yüksek skor",
            "Minimum skor",
            BacktestConfig(
                elde_tutma_gunu=3,
                minimum_skor=70,
                baslangic_sermayesi=100_000.0,
                pozisyon_orani=1.0,
                islem_maliyeti_orani=0.0,
                zarar_durdur_orani=0.05,
                hedef_orani=0.10,
            ),
        ),
    )

    rapor = ParameterSensitivityAnalyzer().analiz_et(
        sembol="AAA.IS",
        fiyat_verisi=fiyat_verisi_olustur(),
        sinyaller=sinyaller_olustur(),
        senaryolar=senaryolar,
    )

    assert rapor.senaryo_sayisi == 2
    assert rapor.baz_sonuc.islem_sayisi == 3
    assert rapor.sonucu_bul("Yüksek skor").islem_sayisi == 1


def test_rapor_getiri_ve_gunluk_dusus_metriklerini_uretir() -> None:
    baz = baz_ayar()
    rapor = ParameterSensitivityAnalyzer().analiz_et(
        sembol="AAA.IS",
        fiyat_verisi=fiyat_verisi_olustur(),
        sinyaller=sinyaller_olustur(),
        senaryolar=(
            ParameterScenario("Baz", "Baz ayarlar", baz),
        ),
    )

    sonuc = rapor.baz_sonuc

    assert sonuc.islem_sayisi == 3
    assert sonuc.toplam_getiri_orani > 0
    assert sonuc.yilliklandirilmis_getiri_orani > 0
    assert sonuc.maksimum_dusus_orani >= 0
    assert sonuc.getiri_dusus_orani is not None


def test_islem_yoksa_sifir_performans_raporlanir() -> None:
    ayar = BacktestConfig(
        elde_tutma_gunu=3,
        minimum_skor=100,
        islem_maliyeti_orani=0.0,
    )
    rapor = ParameterSensitivityAnalyzer().analiz_et(
        sembol="AAA.IS",
        fiyat_verisi=fiyat_verisi_olustur(),
        sinyaller=sinyaller_olustur(),
        senaryolar=(
            ParameterScenario("Baz", "Baz ayarlar", ayar),
        ),
    )

    sonuc = rapor.baz_sonuc

    assert sonuc.islem_sayisi == 0
    assert sonuc.toplam_getiri_orani == 0.0
    assert sonuc.maksimum_dusus_orani == 0.0
    assert sonuc.getiri_dusus_orani is None
    assert rapor.olumlu_senaryo_sayisi == 0


def test_ozet_medyan_araliklar_ve_olumlu_oran_hesaplanir() -> None:
    baz = baz_ayar()
    rapor = ParameterSensitivityAnalyzer().analiz_et(
        sembol="AAA.IS",
        fiyat_verisi=fiyat_verisi_olustur(),
        sinyaller=sinyaller_olustur(),
        senaryolar=(
            ParameterScenario("Baz", "Baz ayarlar", baz),
            ParameterScenario(
                "Skor 70",
                "Minimum skor",
                BacktestConfig(
                    elde_tutma_gunu=3,
                    minimum_skor=70,
                    islem_maliyeti_orani=0.0,
                    zarar_durdur_orani=0.05,
                    hedef_orani=0.10,
                ),
            ),
            ParameterScenario(
                "Skor 100",
                "Minimum skor",
                BacktestConfig(
                    elde_tutma_gunu=3,
                    minimum_skor=100,
                    islem_maliyeti_orani=0.0,
                    zarar_durdur_orani=0.05,
                    hedef_orani=0.10,
                ),
            ),
        ),
    )

    getiriler = sorted(
        sonuc.toplam_getiri_orani
        for sonuc in rapor.sonuclar
    )

    assert rapor.medyan_getiri_orani == pytest.approx(
        getiriler[1]
    )
    assert rapor.minimum_getiri_orani == pytest.approx(
        getiriler[0]
    )
    assert rapor.maksimum_getiri_orani == pytest.approx(
        getiriler[-1]
    )
    assert 0.0 <= rapor.olumlu_senaryo_orani <= 1.0


def test_tekrarlanan_senaryo_adi_reddedilir() -> None:
    baz = baz_ayar()

    with pytest.raises(
        ParameterSensitivityError,
        match="benzersiz",
    ):
        ParameterSensitivityAnalyzer().analiz_et(
            sembol="AAA.IS",
            fiyat_verisi=fiyat_verisi_olustur(),
            sinyaller=sinyaller_olustur(),
            senaryolar=(
                ParameterScenario("Baz", "Baz", baz),
                ParameterScenario("Baz", "Tekrar", baz),
            ),
        )


def test_baz_senaryo_eksikse_veya_liste_bossa_hata_verir() -> None:
    analizci = ParameterSensitivityAnalyzer()

    with pytest.raises(
        ParameterSensitivityError,
        match="En az bir",
    ):
        analizci.analiz_et(
            sembol="AAA.IS",
            fiyat_verisi=fiyat_verisi_olustur(),
            sinyaller=sinyaller_olustur(),
            senaryolar=(),
        )

    with pytest.raises(
        ParameterSensitivityError,
        match="Baz senaryo",
    ):
        analizci.analiz_et(
            sembol="AAA.IS",
            fiyat_verisi=fiyat_verisi_olustur(),
            sinyaller=sinyaller_olustur(),
            senaryolar=(
                ParameterScenario(
                    "Farklı",
                    "Minimum skor",
                    baz_ayar(),
                ),
            ),
            baz_senaryo_adi="Baz",
        )
