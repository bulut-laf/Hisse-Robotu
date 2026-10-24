from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from statistics import median
from typing import Iterable

import pandas as pd

from .backtest_engine import BacktestEngine, BacktestEngineError
from .backtest_models import BacktestConfig, BacktestSignal
from .daily_equity_curve import DailyEquityCurveAnalyzer, DailyEquityCurveError
from .market_regime_analysis import (
    MarketRegimeAnalysisError,
    MarketRegimeAnalyzer,
    MarketRegimeConfig,
    TREND_YUKSELIS,
)
from .position_overlap import cakisan_islemleri_filtrele
from .rolling_window_analysis import (
    RollingWindowAnalysisError,
    RollingWindowAnalyzer,
    RollingWindowConfig,
    RollingWindowReport,
)


class RegimeFilterImpactError(ValueError):
    """Rejim filtresi etki analizinde oluşan veri veya çalışma hatası."""


@dataclass(frozen=True)
class StrategyImpactMetrics:
    """Tek bir strateji varyantının temel performans ölçümleri."""

    ad: str
    sinyal_sayisi: int
    islem_sayisi: int
    kazanma_orani: float
    toplam_getiri_orani: float
    yilliklandirilmis_getiri_orani: float
    maksimum_dusus_orani: float
    kar_faktoru: float | None
    getiri_dusus_orani: float | None


@dataclass(frozen=True)
class RollingImpactSummary:
    """Baz ve filtreli stratejinin eşlenmiş kayan pencere özeti."""

    toplam_eslesmis_pencere: int
    filtre_ustun_pencere: int
    baz_ustun_pencere: int
    esit_pencere: int
    medyan_getiri_farki_orani: float | None
    minimum_getiri_farki_orani: float | None
    maksimum_getiri_farki_orani: float | None

    @property
    def filtre_ustunluk_orani(self) -> float:
        if self.toplam_eslesmis_pencere == 0:
            return 0.0

        return self.filtre_ustun_pencere / self.toplam_eslesmis_pencere


@dataclass(frozen=True)
class RegimeFilterImpactReport:
    """Baz strateji ile yükseliş trendi filtresinin karşılaştırması."""

    sembol: str
    toplam_sinyal_sayisi: int
    rejimi_belirlenen_sinyal_sayisi: int
    rejimi_belirlenemeyen_sinyal_sayisi: int
    filtreye_uygun_sinyal_sayisi: int
    filtre_disi_sinyal_sayisi: int
    baz: StrategyImpactMetrics
    filtreli: StrategyImpactMetrics
    toplam_getiri_farki_orani: float
    yillik_getiri_farki_orani: float
    maksimum_dusus_farki_orani: float
    islem_sayisi_farki: int
    baz_kayan_pencere: RollingWindowReport
    filtreli_kayan_pencere: RollingWindowReport
    kayan_pencere_ozeti: RollingImpactSummary


class RegimeFilterImpactAnalyzer:
    """
    Baz stratejiyi, yalnızca sinyal gününde yükseliş trendinde olan
    sinyalleri kabul eden deneysel filtreyle karşılaştırır.

    Rejimler yalnızca sinyal gününe kadar bilinen fiyatlarla üretilir.
    Analiz geçmişte en iyi filtreyi seçmez ve ana stratejiyi değiştirmez.
    """

    def __init__(
        self,
        backtest_motoru: BacktestEngine | None = None,
        gunluk_ozsermaye_analizcisi: DailyEquityCurveAnalyzer | None = None,
        rejim_analizcisi: MarketRegimeAnalyzer | None = None,
        kayan_pencere_analizcisi: RollingWindowAnalyzer | None = None,
    ) -> None:
        self._backtest_motoru = backtest_motoru or BacktestEngine()
        self._gunluk_ozsermaye_analizcisi = (
            gunluk_ozsermaye_analizcisi or DailyEquityCurveAnalyzer()
        )
        self._rejim_analizcisi = rejim_analizcisi or MarketRegimeAnalyzer()
        self._kayan_pencere_analizcisi = (
            kayan_pencere_analizcisi or RollingWindowAnalyzer()
        )

    def analiz_et(
        self,
        sembol: str,
        fiyat_verisi: pd.DataFrame,
        sinyaller: Iterable[BacktestSignal],
        backtest_yapilandirmasi: BacktestConfig,
        rejim_yapilandirmasi: MarketRegimeConfig | None = None,
        kayan_pencere_yapilandirmasi: RollingWindowConfig | None = None,
    ) -> RegimeFilterImpactReport:
        temiz_sembol = self._sembolu_hazirla(sembol)
        sinyal_listesi = tuple(
            sorted(
                (
                    sinyal
                    for sinyal in tuple(sinyaller)
                    if sinyal.sembol == temiz_sembol
                ),
                key=lambda sinyal: sinyal.sinyal_tarihi,
            )
        )
        kayan_ayarlar = kayan_pencere_yapilandirmasi or RollingWindowConfig()

        try:
            rejim_raporu = self._rejim_analizcisi.analiz_et(
                sembol=temiz_sembol,
                fiyat_verisi=fiyat_verisi,
                islemler=(),
                backtest_yapilandirmasi=backtest_yapilandirmasi,
                yapilandirma=rejim_yapilandirmasi,
            )
            rejim_haritasi = {
                nokta.tarih: nokta.trend_rejimi
                for nokta in rejim_raporu.gunluk_noktalar
            }
            rejimi_belirlenen = tuple(
                sinyal
                for sinyal in sinyal_listesi
                if sinyal.sinyal_tarihi in rejim_haritasi
            )
            filtreli_sinyaller = tuple(
                sinyal
                for sinyal in rejimi_belirlenen
                if rejim_haritasi[sinyal.sinyal_tarihi] == TREND_YUKSELIS
            )

            baz = self._varyanti_hesapla(
                ad="Baz Strateji",
                sembol=temiz_sembol,
                fiyat_verisi=fiyat_verisi,
                sinyaller=sinyal_listesi,
                backtest_yapilandirmasi=backtest_yapilandirmasi,
            )
            filtreli = self._varyanti_hesapla(
                ad="Yalnızca Yükseliş Trendi",
                sembol=temiz_sembol,
                fiyat_verisi=fiyat_verisi,
                sinyaller=filtreli_sinyaller,
                backtest_yapilandirmasi=backtest_yapilandirmasi,
            )
            baz_kayan = self._kayan_pencere_analizcisi.analiz_et(
                sembol=temiz_sembol,
                fiyat_verisi=fiyat_verisi,
                sinyaller=sinyal_listesi,
                backtest_yapilandirmasi=backtest_yapilandirmasi,
                yapilandirma=kayan_ayarlar,
            )
            filtreli_kayan = self._kayan_pencere_analizcisi.analiz_et(
                sembol=temiz_sembol,
                fiyat_verisi=fiyat_verisi,
                sinyaller=filtreli_sinyaller,
                backtest_yapilandirmasi=backtest_yapilandirmasi,
                yapilandirma=kayan_ayarlar,
            )

        except (
            BacktestEngineError,
            DailyEquityCurveError,
            MarketRegimeAnalysisError,
            RollingWindowAnalysisError,
            ValueError,
        ) as hata:
            raise RegimeFilterImpactError(
                f"Rejim filtresi etki analizi çalıştırılamadı: {hata}"
            ) from hata

        return RegimeFilterImpactReport(
            sembol=temiz_sembol,
            toplam_sinyal_sayisi=len(sinyal_listesi),
            rejimi_belirlenen_sinyal_sayisi=len(rejimi_belirlenen),
            rejimi_belirlenemeyen_sinyal_sayisi=(
                len(sinyal_listesi) - len(rejimi_belirlenen)
            ),
            filtreye_uygun_sinyal_sayisi=len(filtreli_sinyaller),
            filtre_disi_sinyal_sayisi=(
                len(rejimi_belirlenen) - len(filtreli_sinyaller)
            ),
            baz=baz,
            filtreli=filtreli,
            toplam_getiri_farki_orani=(
                filtreli.toplam_getiri_orani - baz.toplam_getiri_orani
            ),
            yillik_getiri_farki_orani=(
                filtreli.yilliklandirilmis_getiri_orani
                - baz.yilliklandirilmis_getiri_orani
            ),
            maksimum_dusus_farki_orani=(
                filtreli.maksimum_dusus_orani - baz.maksimum_dusus_orani
            ),
            islem_sayisi_farki=(filtreli.islem_sayisi - baz.islem_sayisi),
            baz_kayan_pencere=baz_kayan,
            filtreli_kayan_pencere=filtreli_kayan,
            kayan_pencere_ozeti=self._kayan_pencereleri_karsilastir(
                baz_kayan,
                filtreli_kayan,
            ),
        )

    def _varyanti_hesapla(
        self,
        ad: str,
        sembol: str,
        fiyat_verisi: pd.DataFrame,
        sinyaller: tuple[BacktestSignal, ...],
        backtest_yapilandirmasi: BacktestConfig,
    ) -> StrategyImpactMetrics:
        ham_sonuc = self._backtest_motoru.calistir(
            veriler={sembol: fiyat_verisi},
            sinyaller=sinyaller,
            yapilandirma=backtest_yapilandirmasi,
        )
        sonuc = cakisan_islemleri_filtrele(
            sonuc=ham_sonuc,
            yapilandirma=backtest_yapilandirmasi,
        )
        gunluk = self._gunluk_ozsermaye_analizcisi.analiz_et(
            fiyat_verisi=fiyat_verisi,
            islemler=sonuc.islemler,
            baslangic_sermayesi=backtest_yapilandirmasi.baslangic_sermayesi,
            pozisyon_orani=backtest_yapilandirmasi.pozisyon_orani,
            islem_maliyeti_orani=backtest_yapilandirmasi.islem_maliyeti_orani,
        )
        toplam_getiri = sonuc.metrikler.toplam_net_getiri_orani
        maksimum_dusus = gunluk.maksimum_dusus_orani
        takvim_gunu = self._takvim_gunu_sayisi(fiyat_verisi)

        return StrategyImpactMetrics(
            ad=ad,
            sinyal_sayisi=len(sinyaller),
            islem_sayisi=sonuc.metrikler.islem_sayisi,
            kazanma_orani=sonuc.metrikler.kazanma_orani,
            toplam_getiri_orani=toplam_getiri,
            yilliklandirilmis_getiri_orani=(
                self._yilliklandirilmis_getiri(toplam_getiri, takvim_gunu)
            ),
            maksimum_dusus_orani=maksimum_dusus,
            kar_faktoru=sonuc.metrikler.kar_faktoru,
            getiri_dusus_orani=(
                None if maksimum_dusus == 0 else toplam_getiri / maksimum_dusus
            ),
        )

    @staticmethod
    def _kayan_pencereleri_karsilastir(
        baz: RollingWindowReport,
        filtreli: RollingWindowReport,
    ) -> RollingImpactSummary:
        baz_haritasi = {
            (p.baslangic_tarihi, p.bitis_tarihi): p
            for p in baz.pencereler
        }
        farklar: list[float] = []
        filtre_ustun = 0
        baz_ustun = 0
        esit = 0

        for pencere in filtreli.pencereler:
            anahtar = (pencere.baslangic_tarihi, pencere.bitis_tarihi)
            baz_pencere = baz_haritasi.get(anahtar)

            if (
                baz_pencere is None
                or not baz_pencere.yeterli_islem_mi
                or not pencere.yeterli_islem_mi
            ):
                continue

            fark = (
                pencere.toplam_getiri_orani
                - baz_pencere.toplam_getiri_orani
            )
            farklar.append(fark)

            if abs(fark) < 1e-12:
                esit += 1
            elif fark > 0:
                filtre_ustun += 1
            else:
                baz_ustun += 1

        return RollingImpactSummary(
            toplam_eslesmis_pencere=len(farklar),
            filtre_ustun_pencere=filtre_ustun,
            baz_ustun_pencere=baz_ustun,
            esit_pencere=esit,
            medyan_getiri_farki_orani=(median(farklar) if farklar else None),
            minimum_getiri_farki_orani=(min(farklar) if farklar else None),
            maksimum_getiri_farki_orani=(max(farklar) if farklar else None),
        )

    @staticmethod
    def _sembolu_hazirla(sembol: str) -> str:
        temiz = sembol.strip().upper()

        if not temiz:
            raise RegimeFilterImpactError("Hisse sembolü boş olamaz.")

        if "." not in temiz:
            temiz += ".IS"

        return temiz

    @staticmethod
    def _takvim_gunu_sayisi(fiyat_verisi: pd.DataFrame) -> int:
        if not isinstance(fiyat_verisi, pd.DataFrame) or fiyat_verisi.empty:
            raise RegimeFilterImpactError("Fiyat verisi boş olamaz.")

        tarihler = pd.to_datetime(fiyat_verisi.index, errors="coerce")

        if tarihler.isna().any():
            raise RegimeFilterImpactError("Fiyat verisinde geçersiz tarihler var.")

        gun = (tarihler.max().date() - tarihler.min().date()).days
        return max(gun, 1)

    @staticmethod
    def _yilliklandirilmis_getiri(
        toplam_getiri_orani: float,
        takvim_gunu_sayisi: int,
    ) -> float:
        if not isfinite(toplam_getiri_orani) or toplam_getiri_orani <= -1:
            raise RegimeFilterImpactError("Toplam getiri yıllıklandırılamıyor.")

        return (1 + toplam_getiri_orani) ** (365 / takvim_gunu_sayisi) - 1
