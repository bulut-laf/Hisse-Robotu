from __future__ import annotations

from dataclasses import dataclass, replace
from math import isfinite
from statistics import median
from typing import Iterable

import pandas as pd

from .backtest_engine import (
    BacktestEngine,
    BacktestEngineError,
)
from .backtest_models import (
    BacktestConfig,
    BacktestSignal,
)
from .daily_equity_curve import (
    DailyEquityCurveAnalyzer,
    DailyEquityCurveError,
)
from .position_overlap import cakisan_islemleri_filtrele


class ParameterSensitivityError(ValueError):
    """Parametre duyarlılığı analizinde oluşan hata."""


@dataclass(frozen=True)
class ParameterScenario:
    """Tek bir backtest parametre senaryosu."""

    ad: str
    degisen_parametre: str
    yapilandirma: BacktestConfig

    def __post_init__(self) -> None:
        temiz_ad = self.ad.strip()
        temiz_parametre = self.degisen_parametre.strip()

        if not temiz_ad:
            raise ValueError("Senaryo adı boş olamaz.")

        if not temiz_parametre:
            raise ValueError(
                "Değişen parametre açıklaması boş olamaz."
            )

        object.__setattr__(self, "ad", temiz_ad)
        object.__setattr__(
            self,
            "degisen_parametre",
            temiz_parametre,
        )


@dataclass(frozen=True)
class ParameterScenarioResult:
    """Tek bir senaryonun performans sonucu."""

    senaryo: ParameterScenario
    islem_sayisi: int
    kazanma_orani: float
    toplam_getiri_orani: float
    yilliklandirilmis_getiri_orani: float
    maksimum_dusus_orani: float
    guncel_dusus_orani: float
    kar_faktoru: float | None
    getiri_dusus_orani: float | None


@dataclass(frozen=True)
class ParameterSensitivityReport:
    """Tek değişkenli parametre duyarlılığı raporu."""

    sembol: str
    baz_senaryo_adi: str
    sonuclar: tuple[ParameterScenarioResult, ...]
    olumlu_senaryo_sayisi: int
    medyan_getiri_orani: float
    minimum_getiri_orani: float
    maksimum_getiri_orani: float
    minimum_maksimum_dusus_orani: float
    maksimum_maksimum_dusus_orani: float

    @property
    def senaryo_sayisi(self) -> int:
        return len(self.sonuclar)

    @property
    def olumlu_senaryo_orani(self) -> float:
        if not self.sonuclar:
            return 0.0

        return self.olumlu_senaryo_sayisi / len(self.sonuclar)

    @property
    def baz_sonuc(self) -> ParameterScenarioResult:
        for sonuc in self.sonuclar:
            if sonuc.senaryo.ad == self.baz_senaryo_adi:
                return sonuc

        raise ParameterSensitivityError(
            "Baz senaryo sonucu raporda bulunamadı."
        )

    def sonucu_bul(
        self,
        senaryo_adi: str,
    ) -> ParameterScenarioResult:
        temiz_ad = senaryo_adi.strip()

        for sonuc in self.sonuclar:
            if sonuc.senaryo.ad == temiz_ad:
                return sonuc

        raise KeyError(
            f"Senaryo sonucu bulunamadı: {temiz_ad}"
        )


class ParameterSensitivityAnalyzer:
    """
    Aynı fiyat verisi ve aynı tarihsel sinyal kümesi üzerinde
    backtest ayarlarını tek değişkenli senaryolarla karşılaştırır.

    Sinyaller her senaryo için yeniden üretilmez. Böylece parametre
    karşılaştırması aynı bilgi seti üzerinde ve daha düşük maliyetle
    yapılır. Aynı sembolde çakışan pozisyonlar her senaryoda elenir.
    """

    def __init__(
        self,
        backtest_motoru: BacktestEngine | None = None,
        gunluk_ozsermaye_analizcisi: (
            DailyEquityCurveAnalyzer | None
        ) = None,
    ) -> None:
        self._backtest_motoru = (
            backtest_motoru
            if backtest_motoru is not None
            else BacktestEngine()
        )
        self._gunluk_ozsermaye_analizcisi = (
            gunluk_ozsermaye_analizcisi
            if gunluk_ozsermaye_analizcisi is not None
            else DailyEquityCurveAnalyzer()
        )

    def analiz_et(
        self,
        sembol: str,
        fiyat_verisi: pd.DataFrame,
        sinyaller: Iterable[BacktestSignal],
        senaryolar: Iterable[ParameterScenario],
        baz_senaryo_adi: str = "Baz",
    ) -> ParameterSensitivityReport:
        temiz_sembol = sembol.strip().upper()

        if not temiz_sembol:
            raise ParameterSensitivityError(
                "Hisse sembolü boş olamaz."
            )

        if not isinstance(fiyat_verisi, pd.DataFrame):
            raise ParameterSensitivityError(
                "Fiyat verisi pandas DataFrame olmalıdır."
            )

        if fiyat_verisi.empty:
            raise ParameterSensitivityError(
                "Fiyat verisi boş olamaz."
            )

        tarihler = pd.to_datetime(
            fiyat_verisi.index,
            errors="coerce",
        )

        if tarihler.isna().any():
            raise ParameterSensitivityError(
                "Fiyat verisinde geçersiz tarihler var."
            )

        ilk_tarih = tarihler.min().date()
        son_tarih = tarihler.max().date()
        takvim_gunu_sayisi = (son_tarih - ilk_tarih).days

        if takvim_gunu_sayisi <= 0:
            raise ParameterSensitivityError(
                "Duyarlılık analizi için en az iki farklı "
                "tarih gereklidir."
            )

        senaryo_listesi = tuple(senaryolar)

        if not senaryo_listesi:
            raise ParameterSensitivityError(
                "En az bir parametre senaryosu gereklidir."
            )

        adlar = tuple(
            senaryo.ad
            for senaryo in senaryo_listesi
        )

        if len(set(adlar)) != len(adlar):
            raise ParameterSensitivityError(
                "Senaryo adları benzersiz olmalıdır."
            )

        temiz_baz_adi = baz_senaryo_adi.strip()

        if temiz_baz_adi not in adlar:
            raise ParameterSensitivityError(
                "Baz senaryo, senaryo listesinde bulunmalıdır."
            )

        sinyal_listesi = tuple(sinyaller)
        sonuclar: list[ParameterScenarioResult] = []

        for senaryo in senaryo_listesi:
            try:
                ham_sonuc = self._backtest_motoru.calistir(
                    veriler={temiz_sembol: fiyat_verisi},
                    sinyaller=sinyal_listesi,
                    yapilandirma=senaryo.yapilandirma,
                )

                sonuc = cakisan_islemleri_filtrele(
                    sonuc=ham_sonuc,
                    yapilandirma=senaryo.yapilandirma,
                )

                gunluk_rapor = (
                    self._gunluk_ozsermaye_analizcisi
                    .analiz_et(
                        fiyat_verisi=fiyat_verisi,
                        islemler=sonuc.islemler,
                        baslangic_sermayesi=(
                            senaryo.yapilandirma
                            .baslangic_sermayesi
                        ),
                        pozisyon_orani=(
                            senaryo.yapilandirma
                            .pozisyon_orani
                        ),
                        islem_maliyeti_orani=(
                            senaryo.yapilandirma
                            .islem_maliyeti_orani
                        ),
                    )
                )

            except (
                BacktestEngineError,
                DailyEquityCurveError,
                ValueError,
            ) as hata:
                raise ParameterSensitivityError(
                    f"{senaryo.ad} senaryosu çalıştırılamadı: "
                    f"{hata}"
                ) from hata

            toplam_getiri = (
                sonuc.metrikler.toplam_net_getiri_orani
            )
            yillik_getiri = (
                self._yilliklandirilmis_getiriyi_hesapla(
                    toplam_getiri_orani=toplam_getiri,
                    takvim_gunu_sayisi=takvim_gunu_sayisi,
                )
            )
            maksimum_dusus = (
                gunluk_rapor.maksimum_dusus_orani
            )

            sonuclar.append(
                ParameterScenarioResult(
                    senaryo=senaryo,
                    islem_sayisi=(
                        sonuc.metrikler.islem_sayisi
                    ),
                    kazanma_orani=(
                        sonuc.metrikler.kazanma_orani
                    ),
                    toplam_getiri_orani=toplam_getiri,
                    yilliklandirilmis_getiri_orani=(
                        yillik_getiri
                    ),
                    maksimum_dusus_orani=maksimum_dusus,
                    guncel_dusus_orani=(
                        gunluk_rapor.guncel_dusus_orani
                    ),
                    kar_faktoru=(
                        sonuc.metrikler.kar_faktoru
                    ),
                    getiri_dusus_orani=(
                        toplam_getiri / maksimum_dusus
                        if maksimum_dusus > 0
                        else None
                    ),
                )
            )

        sonuc_tuple = tuple(sonuclar)
        getiriler = tuple(
            sonuc.toplam_getiri_orani
            for sonuc in sonuc_tuple
        )
        maksimum_dususler = tuple(
            sonuc.maksimum_dusus_orani
            for sonuc in sonuc_tuple
        )

        return ParameterSensitivityReport(
            sembol=temiz_sembol,
            baz_senaryo_adi=temiz_baz_adi,
            sonuclar=sonuc_tuple,
            olumlu_senaryo_sayisi=sum(
                1
                for getiri in getiriler
                if getiri > 0
            ),
            medyan_getiri_orani=float(median(getiriler)),
            minimum_getiri_orani=min(getiriler),
            maksimum_getiri_orani=max(getiriler),
            minimum_maksimum_dusus_orani=min(
                maksimum_dususler
            ),
            maksimum_maksimum_dusus_orani=max(
                maksimum_dususler
            ),
        )

    @staticmethod
    def _yilliklandirilmis_getiriyi_hesapla(
        toplam_getiri_orani: float,
        takvim_gunu_sayisi: int,
    ) -> float:
        if not isfinite(toplam_getiri_orani):
            raise ParameterSensitivityError(
                "Toplam getiri sonlu olmalıdır."
            )

        getiri_carpani = 1.0 + toplam_getiri_orani

        if getiri_carpani <= 0:
            return -1.0

        return (
            getiri_carpani
            ** (365.0 / takvim_gunu_sayisi)
            - 1.0
        )


def varsayilan_tek_degisken_senaryolari(
    baz_yapilandirma: BacktestConfig,
) -> tuple[ParameterScenario, ...]:
    """
    Baz ayarın çevresinde tek değişkenli yerel senaryolar üretir.

    Bu fonksiyon kombinasyon optimizasyonu yapmaz. Her senaryoda yalnızca
    minimum skor, elde tutma, zarar durdur veya hedef değerlerinden biri
    değiştirilir.
    """
    senaryolar: list[ParameterScenario] = [
        ParameterScenario(
            ad="Baz",
            degisen_parametre="Baz ayarlar",
            yapilandirma=baz_yapilandirma,
        )
    ]

    skor_degerleri = (
        max(0, baz_yapilandirma.minimum_skor - 5),
        min(100, baz_yapilandirma.minimum_skor + 5),
    )
    elde_tutma_degerleri = (
        max(1, baz_yapilandirma.elde_tutma_gunu - 5),
        min(30, baz_yapilandirma.elde_tutma_gunu + 5),
    )

    for deger in skor_degerleri:
        if deger != baz_yapilandirma.minimum_skor:
            senaryolar.append(
                ParameterScenario(
                    ad=f"Minimum skor {deger}",
                    degisen_parametre="Minimum skor",
                    yapilandirma=replace(
                        baz_yapilandirma,
                        minimum_skor=deger,
                    ),
                )
            )

    for deger in elde_tutma_degerleri:
        if deger != baz_yapilandirma.elde_tutma_gunu:
            senaryolar.append(
                ParameterScenario(
                    ad=f"Elde tutma {deger}",
                    degisen_parametre="Elde tutma",
                    yapilandirma=replace(
                        baz_yapilandirma,
                        elde_tutma_gunu=deger,
                    ),
                )
            )

    if baz_yapilandirma.zarar_durdur_orani is not None:
        stop_yuzdesi = (
            baz_yapilandirma.zarar_durdur_orani * 100.0
        )
        stop_degerleri = (
            max(0.1, stop_yuzdesi - 2.0),
            min(99.9, stop_yuzdesi + 2.0),
        )

        for yuzde in stop_degerleri:
            oran = yuzde / 100.0
            if not isfinite(oran) or oran <= 0 or oran >= 1:
                continue

            if abs(
                oran
                - baz_yapilandirma.zarar_durdur_orani
            ) < 1e-12:
                continue

            senaryolar.append(
                ParameterScenario(
                    ad=f"Zarar durdur {yuzde:.1f}%",
                    degisen_parametre="Zarar durdur",
                    yapilandirma=replace(
                        baz_yapilandirma,
                        zarar_durdur_orani=oran,
                    ),
                )
            )

    if baz_yapilandirma.hedef_orani is not None:
        hedef_yuzdesi = baz_yapilandirma.hedef_orani * 100.0
        hedef_degerleri = (
            max(0.1, hedef_yuzdesi - 3.0),
            min(99.9, hedef_yuzdesi + 5.0),
        )

        for yuzde in hedef_degerleri:
            oran = yuzde / 100.0
            if not isfinite(oran) or oran <= 0 or oran >= 1:
                continue

            if abs(
                oran - baz_yapilandirma.hedef_orani
            ) < 1e-12:
                continue

            senaryolar.append(
                ParameterScenario(
                    ad=f"Hedef {yuzde:.1f}%",
                    degisen_parametre="Hedef",
                    yapilandirma=replace(
                        baz_yapilandirma,
                        hedef_orani=oran,
                    ),
                )
            )

    return tuple(senaryolar)
