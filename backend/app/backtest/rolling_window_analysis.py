from __future__ import annotations

from dataclasses import dataclass
from datetime import date
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


class RollingWindowAnalysisError(ValueError):
    """Kayan pencere sağlamlık analizinde oluşan hata."""


@dataclass(frozen=True)
class RollingWindowConfig:
    """Kayan pencere üretim ve yeterlilik ayarları."""

    pencere_bar_sayisi: int = 252
    adim_bar_sayisi: int = 63
    minimum_islem_sayisi: int = 5

    def __post_init__(self) -> None:
        if self.pencere_bar_sayisi < 2:
            raise ValueError(
                "Pencere bar sayısı en az 2 olmalıdır."
            )

        if self.adim_bar_sayisi < 1:
            raise ValueError(
                "Adım bar sayısı en az 1 olmalıdır."
            )

        if self.adim_bar_sayisi > self.pencere_bar_sayisi:
            raise ValueError(
                "Adım bar sayısı pencere bar sayısından büyük olamaz."
            )

        if self.minimum_islem_sayisi < 1:
            raise ValueError(
                "Minimum işlem sayısı en az 1 olmalıdır."
            )


@dataclass(frozen=True)
class RollingWindowResult:
    """Tek bir kayan pencerenin sabit strateji sonucu."""

    sira: int
    baslangic_tarihi: date
    bitis_tarihi: date
    bar_sayisi: int
    sinyal_sayisi: int
    islem_sayisi: int
    kazanma_orani: float
    toplam_getiri_orani: float
    yilliklandirilmis_getiri_orani: float
    maksimum_dusus_orani: float
    guncel_dusus_orani: float
    kar_faktoru: float | None
    getiri_dusus_orani: float | None
    yeterli_islem_mi: bool


@dataclass(frozen=True)
class RollingWindowReport:
    """Sabit ayarların dönemler boyunca sağlamlık özeti."""

    sembol: str
    yapilandirma: RollingWindowConfig
    pencereler: tuple[RollingWindowResult, ...]
    degerlendirilen_pencere_sayisi: int
    pozitif_pencere_sayisi: int
    medyan_toplam_getiri_orani: float | None
    medyan_yilliklandirilmis_getiri_orani: float | None
    minimum_toplam_getiri_orani: float | None
    maksimum_toplam_getiri_orani: float | None
    minimum_maksimum_dusus_orani: float | None
    maksimum_maksimum_dusus_orani: float | None
    en_iyi_pencere: RollingWindowResult | None
    en_zayif_pencere: RollingWindowResult | None

    @property
    def pencere_sayisi(self) -> int:
        return len(self.pencereler)

    @property
    def yetersiz_pencere_sayisi(self) -> int:
        return (
            self.pencere_sayisi
            - self.degerlendirilen_pencere_sayisi
        )

    @property
    def pozitif_pencere_orani(self) -> float:
        if self.degerlendirilen_pencere_sayisi == 0:
            return 0.0

        return (
            self.pozitif_pencere_sayisi
            / self.degerlendirilen_pencere_sayisi
        )


class RollingWindowAnalyzer:
    """
    Sabit backtest ayarlarını örtüşen zaman pencerelerinde değerlendirir.

    Tarihsel sinyaller bir kez üretilmiş olmalıdır. Her pencere yalnızca
    nominal pencere tarihleri içindeki sinyalleri kullanır. İşlemler,
    pencere sonunda yapay biçimde kesilmemeleri için tam fiyat verisi
    üzerinde tamamlanır. Bu analiz parametre optimizasyonu yapmaz.
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
        backtest_yapilandirmasi: BacktestConfig,
        yapilandirma: RollingWindowConfig | None = None,
    ) -> RollingWindowReport:
        ayarlar = (
            yapilandirma
            if yapilandirma is not None
            else RollingWindowConfig()
        )
        temiz_sembol = self._sembolu_hazirla(sembol)
        hazir_veri = self._fiyat_verisini_hazirla(fiyat_verisi)

        if len(hazir_veri) < ayarlar.pencere_bar_sayisi:
            raise RollingWindowAnalysisError(
                "Fiyat verisi pencere bar sayısından kısa olamaz."
            )

        sinyal_listesi = tuple(
            sinyal
            for sinyal in tuple(sinyaller)
            if sinyal.sembol == temiz_sembol
        )
        pencere_baslangiclari = self._pencere_baslangiclarini_uret(
            toplam_bar_sayisi=len(hazir_veri),
            pencere_bar_sayisi=ayarlar.pencere_bar_sayisi,
            adim_bar_sayisi=ayarlar.adim_bar_sayisi,
        )
        sonuclar: list[RollingWindowResult] = []

        for sira, baslangic_konumu in enumerate(
            pencere_baslangiclari,
            start=1,
        ):
            bitis_konumu = (
                baslangic_konumu
                + ayarlar.pencere_bar_sayisi
            )
            pencere_verisi = hazir_veri.iloc[
                baslangic_konumu:bitis_konumu
            ]
            baslangic_tarihi = pencere_verisi.index[0].date()
            bitis_tarihi = pencere_verisi.index[-1].date()
            pencere_sinyalleri = tuple(
                sinyal
                for sinyal in sinyal_listesi
                if (
                    baslangic_tarihi
                    <= sinyal.sinyal_tarihi
                    <= bitis_tarihi
                )
            )

            try:
                ham_sonuc = self._backtest_motoru.calistir(
                    veriler={temiz_sembol: hazir_veri},
                    sinyaller=pencere_sinyalleri,
                    yapilandirma=backtest_yapilandirmasi,
                )
                sonuc = cakisan_islemleri_filtrele(
                    sonuc=ham_sonuc,
                    yapilandirma=backtest_yapilandirmasi,
                )
                gunluk_rapor = (
                    self._gunluk_ozsermaye_analizcisi
                    .analiz_et(
                        fiyat_verisi=hazir_veri,
                        islemler=sonuc.islemler,
                        baslangic_sermayesi=(
                            backtest_yapilandirmasi
                            .baslangic_sermayesi
                        ),
                        pozisyon_orani=(
                            backtest_yapilandirmasi
                            .pozisyon_orani
                        ),
                        islem_maliyeti_orani=(
                            backtest_yapilandirmasi
                            .islem_maliyeti_orani
                        ),
                    )
                )

            except (
                BacktestEngineError,
                DailyEquityCurveError,
                ValueError,
            ) as hata:
                raise RollingWindowAnalysisError(
                    f"{sira}. pencere çalıştırılamadı: {hata}"
                ) from hata

            toplam_getiri = (
                sonuc.metrikler.toplam_net_getiri_orani
            )
            maksimum_dusus = gunluk_rapor.maksimum_dusus_orani
            takvim_gunu_sayisi = (
                bitis_tarihi - baslangic_tarihi
            ).days
            yillik_getiri = self._yilliklandirilmis_getiriyi_hesapla(
                toplam_getiri_orani=toplam_getiri,
                takvim_gunu_sayisi=takvim_gunu_sayisi,
            )
            islem_sayisi = sonuc.metrikler.islem_sayisi

            sonuclar.append(
                RollingWindowResult(
                    sira=sira,
                    baslangic_tarihi=baslangic_tarihi,
                    bitis_tarihi=bitis_tarihi,
                    bar_sayisi=len(pencere_verisi),
                    sinyal_sayisi=len(pencere_sinyalleri),
                    islem_sayisi=islem_sayisi,
                    kazanma_orani=sonuc.metrikler.kazanma_orani,
                    toplam_getiri_orani=toplam_getiri,
                    yilliklandirilmis_getiri_orani=yillik_getiri,
                    maksimum_dusus_orani=maksimum_dusus,
                    guncel_dusus_orani=(
                        gunluk_rapor.guncel_dusus_orani
                    ),
                    kar_faktoru=sonuc.metrikler.kar_faktoru,
                    getiri_dusus_orani=(
                        toplam_getiri / maksimum_dusus
                        if maksimum_dusus > 0
                        else None
                    ),
                    yeterli_islem_mi=(
                        islem_sayisi
                        >= ayarlar.minimum_islem_sayisi
                    ),
                )
            )

        pencere_tuple = tuple(sonuclar)
        yeterli_pencereler = tuple(
            pencere
            for pencere in pencere_tuple
            if pencere.yeterli_islem_mi
        )

        if not yeterli_pencereler:
            return RollingWindowReport(
                sembol=temiz_sembol,
                yapilandirma=ayarlar,
                pencereler=pencere_tuple,
                degerlendirilen_pencere_sayisi=0,
                pozitif_pencere_sayisi=0,
                medyan_toplam_getiri_orani=None,
                medyan_yilliklandirilmis_getiri_orani=None,
                minimum_toplam_getiri_orani=None,
                maksimum_toplam_getiri_orani=None,
                minimum_maksimum_dusus_orani=None,
                maksimum_maksimum_dusus_orani=None,
                en_iyi_pencere=None,
                en_zayif_pencere=None,
            )

        toplam_getiriler = tuple(
            pencere.toplam_getiri_orani
            for pencere in yeterli_pencereler
        )
        yillik_getiriler = tuple(
            pencere.yilliklandirilmis_getiri_orani
            for pencere in yeterli_pencereler
        )
        maksimum_dususler = tuple(
            pencere.maksimum_dusus_orani
            for pencere in yeterli_pencereler
        )

        return RollingWindowReport(
            sembol=temiz_sembol,
            yapilandirma=ayarlar,
            pencereler=pencere_tuple,
            degerlendirilen_pencere_sayisi=len(
                yeterli_pencereler
            ),
            pozitif_pencere_sayisi=sum(
                1
                for getiri in toplam_getiriler
                if getiri > 0
            ),
            medyan_toplam_getiri_orani=float(
                median(toplam_getiriler)
            ),
            medyan_yilliklandirilmis_getiri_orani=float(
                median(yillik_getiriler)
            ),
            minimum_toplam_getiri_orani=min(toplam_getiriler),
            maksimum_toplam_getiri_orani=max(toplam_getiriler),
            minimum_maksimum_dusus_orani=min(maksimum_dususler),
            maksimum_maksimum_dusus_orani=max(maksimum_dususler),
            en_iyi_pencere=max(
                yeterli_pencereler,
                key=lambda pencere: pencere.toplam_getiri_orani,
            ),
            en_zayif_pencere=min(
                yeterli_pencereler,
                key=lambda pencere: pencere.toplam_getiri_orani,
            ),
        )

    @staticmethod
    def _sembolu_hazirla(sembol: str) -> str:
        temiz_sembol = sembol.strip().upper()

        if not temiz_sembol:
            raise RollingWindowAnalysisError(
                "Hisse sembolü boş olamaz."
            )

        if "." not in temiz_sembol:
            temiz_sembol += ".IS"

        return temiz_sembol

    @staticmethod
    def _fiyat_verisini_hazirla(
        fiyat_verisi: pd.DataFrame,
    ) -> pd.DataFrame:
        if not isinstance(fiyat_verisi, pd.DataFrame):
            raise RollingWindowAnalysisError(
                "Fiyat verisi pandas DataFrame olmalıdır."
            )

        if fiyat_verisi.empty:
            raise RollingWindowAnalysisError(
                "Fiyat verisi boş olamaz."
            )

        kopya = fiyat_verisi.copy()
        tarihler = pd.to_datetime(kopya.index, errors="coerce")

        if tarihler.isna().any():
            raise RollingWindowAnalysisError(
                "Fiyat verisinde geçersiz tarihler var."
            )

        if tarihler.tz is not None:
            tarihler = tarihler.tz_localize(None)

        kopya.index = tarihler.normalize()
        kopya = kopya.sort_index()

        if kopya.index.has_duplicates:
            raise RollingWindowAnalysisError(
                "Fiyat verisinde tekrarlanan tarihler var."
            )

        return kopya

    @staticmethod
    def _pencere_baslangiclarini_uret(
        toplam_bar_sayisi: int,
        pencere_bar_sayisi: int,
        adim_bar_sayisi: int,
    ) -> tuple[int, ...]:
        son_baslangic = toplam_bar_sayisi - pencere_bar_sayisi
        baslangiclar = list(
            range(0, son_baslangic + 1, adim_bar_sayisi)
        )

        if baslangiclar[-1] != son_baslangic:
            baslangiclar.append(son_baslangic)

        return tuple(baslangiclar)

    @staticmethod
    def _yilliklandirilmis_getiriyi_hesapla(
        toplam_getiri_orani: float,
        takvim_gunu_sayisi: int,
    ) -> float:
        if not isfinite(toplam_getiri_orani):
            raise RollingWindowAnalysisError(
                "Toplam getiri sonlu olmalıdır."
            )

        if takvim_gunu_sayisi <= 0:
            raise RollingWindowAnalysisError(
                "Yıllıklandırma için pozitif gün sayısı gereklidir."
            )

        getiri_carpani = 1.0 + toplam_getiri_orani

        if getiri_carpani <= 0:
            return -1.0

        return (
            getiri_carpani
            ** (365.0 / takvim_gunu_sayisi)
            - 1.0
        )
