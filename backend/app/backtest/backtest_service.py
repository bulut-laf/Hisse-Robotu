from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol

import pandas as pd

from ..analysis.stock_analyzer import (
    StockAnalyzer,
    StockAnalyzerError,
)
from ..data.market_data import (
    MarketDataError,
    fiyat_verisi_getir,
)
from .analysis_context import (
    AnalysisContext,
    AnalysisContextError,
    analiz_baglamini_olustur,
)
from .analysis_profile import (
    AnalysisProfile,
    GECERLI_INDIRME_DONEMLERI,
)
from .backtest_engine import (
    BacktestEngine,
    BacktestEngineError,
    BacktestResult,
)
from .backtest_models import BacktestConfig
from .benchmark_comparison import (
    BenchmarkComparisonAnalyzer,
    BenchmarkComparisonError,
    BenchmarkComparisonReport,
)
from .daily_equity_curve import (
    DailyEquityCurveAnalyzer,
    DailyEquityCurveError,
    DailyEquityCurveReport,
)
from .equity_curve import (
    EquityCurveAnalyzer,
    EquityCurveError,
    EquityCurveReport,
)
from .historical_signal_generator import (
    HistoricalSignalGenerationResult,
    HistoricalSignalGenerator,
    HistoricalSignalGeneratorConfig,
    HistoricalSignalGeneratorError,
)
from .performance_breakdown import (
    PerformanceBreakdownAnalyzer,
    PerformanceBreakdownError,
    PerformanceBreakdownReport,
)
from .position_overlap import (
    CAKISMA_NEDENI,
    cakisan_islemleri_filtrele,
)




class BacktestServiceError(Exception):
    """Backtest servisinin veri veya çalışma hatası."""


class HistoricalAnalyzerProtocol(Protocol):
    """Geçmiş fiyat penceresini analiz edebilen nesne."""

    def veriden_analiz_et(
        self,
        sembol: str,
        fiyat_verisi: pd.DataFrame,
    ) -> object:
        ...


VeriGetirici = Callable[..., pd.DataFrame]


@dataclass(frozen=True)
class BacktestServiceConfig:
    """Gerçek piyasa verili backtest servis ayarları."""

    islem_gunu: int = 750
    indirme_donemi: str = "5y"
    yalnizca_tamamlanmis_gunler: bool = True
    pozisyon_cakismalarini_engelle: bool = True

    sinyal_ayarlari: HistoricalSignalGeneratorConfig = field(
        default_factory=HistoricalSignalGeneratorConfig
    )

    backtest_ayarlari: BacktestConfig = field(
        default_factory=BacktestConfig
    )

    def __post_init__(self) -> None:
        if self.islem_gunu <= 0:
            raise ValueError(
                "İşlem günü sayısı pozitif olmalıdır."
            )

        temiz_donem = self.indirme_donemi.strip()

        if not temiz_donem:
            raise ValueError(
                "İndirme dönemi boş olamaz."
            )

        if temiz_donem not in GECERLI_INDIRME_DONEMLERI:
            raise ValueError(
                "Geçersiz indirme dönemi: "
                f"{temiz_donem}. Geçerli değerler: "
                + ", ".join(
                    GECERLI_INDIRME_DONEMLERI
                )
            )

        if not isinstance(
            self.pozisyon_cakismalarini_engelle,
            bool,
        ):
            raise ValueError(
                "Pozisyon çakışma ayarı doğru/yanlış "
                "değeri olmalıdır."
            )

        object.__setattr__(
            self,
            "indirme_donemi",
            temiz_donem,
        )


@dataclass(frozen=True)
class StockBacktestReport:
    """Tek hisse için uçtan uca backtest raporu."""

    sembol: str
    fiyat_bar_sayisi: int
    ilk_fiyat_tarihi: str
    son_fiyat_tarihi: str
    sinyal_uretimi: HistoricalSignalGenerationResult
    backtest_sonucu: BacktestResult
    performans_dagilimi: PerformanceBreakdownReport
    ozsermaye_raporu: EquityCurveReport
    benchmark_karsilastirmasi: BenchmarkComparisonReport
    hizalanmis_benchmark_karsilastirmasi: (
        BenchmarkComparisonReport | None
    ) = None
    gunluk_ozsermaye_raporu: (
        DailyEquityCurveReport | None
    ) = None
    analiz_baglami: AnalysisContext | None = None

    @property
    def uretilen_sinyal_sayisi(self) -> int:
        return self.sinyal_uretimi.sinyal_sayisi

    @property
    def analizde_atlanan_gun_sayisi(self) -> int:
        return self.sinyal_uretimi.atlanan_gun_sayisi

    @property
    def tamamlanan_islem_sayisi(self) -> int:
        return (
            self.backtest_sonucu
            .tamamlanan_islem_sayisi
        )

    @property
    def cakisma_nedeniyle_atlanan_sinyal_sayisi(
        self,
    ) -> int:
        return sum(
            1
            for atlanan
            in self.backtest_sonucu.atlanan_sinyaller
            if CAKISMA_NEDENI in atlanan.neden
        )


class StockBacktestService:
    """
    Piyasa verisini indirir, geçmiş sinyalleri üretir,
    işlemleri simüle eder ve performansı analiz eder.

    Aynı sembolde açık pozisyon varken başlayan yeni
    işlemler varsayılan olarak elenir.

    Tam veri dönemi al-tut referansı korunur. Ayrıca
    ilk kabul edilen işlem girişinden son kabul edilen
    işlem çıkışına kadar hizalanmış karşılaştırma üretilir.
    """

    def __init__(
        self,
        veri_getirici: VeriGetirici = fiyat_verisi_getir,
        analizci: HistoricalAnalyzerProtocol | None = None,
        backtest_motoru: BacktestEngine | None = None,
        performans_analizcisi: (
            PerformanceBreakdownAnalyzer | None
        ) = None,
        ozsermaye_analizcisi: (
            EquityCurveAnalyzer | None
        ) = None,
        benchmark_analizcisi: (
            BenchmarkComparisonAnalyzer | None
        ) = None,
        gunluk_ozsermaye_analizcisi: (
            DailyEquityCurveAnalyzer | None
        ) = None,
    ) -> None:
        if not callable(veri_getirici):
            raise TypeError(
                "Veri getirici çağrılabilir olmalıdır."
            )

        self._veri_getirici = veri_getirici

        self._analizci = (
            analizci
            if analizci is not None
            else StockAnalyzer()
        )

        self._backtest_motoru = (
            backtest_motoru
            if backtest_motoru is not None
            else BacktestEngine()
        )

        self._performans_analizcisi = (
            performans_analizcisi
            if performans_analizcisi is not None
            else PerformanceBreakdownAnalyzer()
        )

        self._ozsermaye_analizcisi = (
            ozsermaye_analizcisi
            if ozsermaye_analizcisi is not None
            else EquityCurveAnalyzer()
        )

        self._benchmark_analizcisi = (
            benchmark_analizcisi
            if benchmark_analizcisi is not None
            else BenchmarkComparisonAnalyzer()
        )

        self._gunluk_ozsermaye_analizcisi = (
            gunluk_ozsermaye_analizcisi
            if gunluk_ozsermaye_analizcisi is not None
            else DailyEquityCurveAnalyzer()
        )

    def calistir(
        self,
        sembol: str,
        yapilandirma: BacktestServiceConfig | None = None,
    ) -> StockBacktestReport:
        ayarlar = (
            yapilandirma
            if yapilandirma is not None
            else BacktestServiceConfig()
        )

        temiz_sembol = self._sembolu_hazirla(
            sembol
        )

        try:
            fiyat_verisi = self._veri_getirici(
                sembol=temiz_sembol,
                islem_gunu=ayarlar.islem_gunu,
                indirme_donemi=ayarlar.indirme_donemi,
                yalnizca_tamamlanmis_gunler=(
                    ayarlar.yalnizca_tamamlanmis_gunler
                ),
            )

            if not isinstance(
                fiyat_verisi,
                pd.DataFrame,
            ):
                raise BacktestServiceError(
                    "Veri getirici pandas DataFrame "
                    "döndürmelidir."
                )

            if fiyat_verisi.empty:
                raise BacktestServiceError(
                    f"{temiz_sembol} için fiyat verisi "
                    "bulunamadı."
                )

            analiz_profili = AnalysisProfile(
                islem_gunu=ayarlar.islem_gunu,
                indirme_donemi=ayarlar.indirme_donemi,
                minimum_bar_sayisi=(
                    ayarlar.sinyal_ayarlari.minimum_bar_sayisi
                ),
                gorunum_secimi=self._gorunum_secimini_bul(
                    ayarlar.sinyal_ayarlari.izin_verilen_gorunumler
                ),
                elde_tutma_gunu=(
                    ayarlar.backtest_ayarlari.elde_tutma_gunu
                ),
                minimum_skor=(
                    ayarlar.backtest_ayarlari.minimum_skor
                ),
                baslangic_sermayesi=(
                    ayarlar.backtest_ayarlari.baslangic_sermayesi
                ),
                pozisyon_yuzde=(
                    ayarlar.backtest_ayarlari.pozisyon_orani * 100.0
                ),
                maliyet_yuzde=(
                    ayarlar.backtest_ayarlari.islem_maliyeti_orani * 100.0
                ),
                stop_yuzde=self._orani_yuzdeye_cevir(
                    ayarlar.backtest_ayarlari.zarar_durdur_orani
                ),
                hedef_yuzde=self._orani_yuzdeye_cevir(
                    ayarlar.backtest_ayarlari.hedef_orani
                ),
            )
            analiz_baglami = analiz_baglamini_olustur(
                fiyat_verisi=fiyat_verisi,
                profil=analiz_profili,
            )

            sinyal_ureticisi = HistoricalSignalGenerator(
                self._analizci.veriden_analiz_et
            )

            sinyal_uretimi = sinyal_ureticisi.uret(
                sembol=temiz_sembol,
                fiyat_verisi=fiyat_verisi,
                yapilandirma=ayarlar.sinyal_ayarlari,
            )

            ham_backtest_sonucu = (
                self._backtest_motoru.calistir(
                    veriler={
                        temiz_sembol: fiyat_verisi,
                    },
                    sinyaller=sinyal_uretimi.sinyaller,
                    yapilandirma=(
                        ayarlar.backtest_ayarlari
                    ),
                )
            )

            if ayarlar.pozisyon_cakismalarini_engelle:
                backtest_sonucu = (
                    cakisan_islemleri_filtrele(
                        sonuc=ham_backtest_sonucu,
                        yapilandirma=(
                            ayarlar.backtest_ayarlari
                        ),
                    )
                )
            else:
                backtest_sonucu = ham_backtest_sonucu

            baslangic_sermayesi = (
                ayarlar
                .backtest_ayarlari
                .baslangic_sermayesi
            )

            pozisyon_orani = (
                ayarlar
                .backtest_ayarlari
                .pozisyon_orani
            )

            islem_maliyeti_orani = (
                ayarlar
                .backtest_ayarlari
                .islem_maliyeti_orani
            )

            performans_dagilimi = (
                self._performans_analizcisi
                .analiz_et(
                    islemler=(
                        backtest_sonucu.islemler
                    ),
                    baslangic_sermayesi=(
                        baslangic_sermayesi
                    ),
                    pozisyon_orani=(
                        pozisyon_orani
                    ),
                )
            )

            ozsermaye_raporu = (
                self._ozsermaye_analizcisi
                .analiz_et(
                    islemler=(
                        backtest_sonucu.islemler
                    ),
                    baslangic_sermayesi=(
                        baslangic_sermayesi
                    ),
                    pozisyon_orani=(
                        pozisyon_orani
                    ),
                )
            )

            gunluk_ozsermaye_raporu: (
                DailyEquityCurveReport | None
            ) = None

            if ayarlar.pozisyon_cakismalarini_engelle:
                gunluk_ozsermaye_raporu = (
                    self._gunluk_ozsermaye_analizcisi
                    .analiz_et(
                        fiyat_verisi=fiyat_verisi,
                        islemler=backtest_sonucu.islemler,
                        baslangic_sermayesi=(
                            baslangic_sermayesi
                        ),
                        pozisyon_orani=pozisyon_orani,
                        islem_maliyeti_orani=(
                            islem_maliyeti_orani
                        ),
                    )
                )

            benchmark_karsilastirmasi = (
                self._benchmark_analizcisi
                .analiz_et(
                    fiyat_verisi=fiyat_verisi,
                    strateji_toplam_getiri_orani=(
                        ozsermaye_raporu
                        .toplam_bilesik_getiri_orani
                    ),
                    strateji_maksimum_dusus_orani=(
                        ozsermaye_raporu
                        .maksimum_dusus_orani
                    ),
                    baslangic_sermayesi=(
                        baslangic_sermayesi
                    ),
                    islem_maliyeti_orani=(
                        islem_maliyeti_orani
                    ),
                )
            )

            hizalanmis_maksimum_dusus_orani = (
                gunluk_ozsermaye_raporu
                .maksimum_dusus_orani
                if (
                    gunluk_ozsermaye_raporu is not None
                    and gunluk_ozsermaye_raporu.noktalar
                )
                else ozsermaye_raporu.maksimum_dusus_orani
            )

            hizalanmis_benchmark_karsilastirmasi = (
                self._hizalanmis_benchmark_olustur(
                    fiyat_verisi=fiyat_verisi,
                    backtest_sonucu=backtest_sonucu,
                    strateji_toplam_getiri_orani=(
                        ozsermaye_raporu
                        .toplam_bilesik_getiri_orani
                    ),
                    strateji_maksimum_dusus_orani=(
                        hizalanmis_maksimum_dusus_orani
                    ),
                    baslangic_sermayesi=(
                        baslangic_sermayesi
                    ),
                    islem_maliyeti_orani=(
                        islem_maliyeti_orani
                    ),
                )
            )

            ilk_tarih, son_tarih = (
                self._tarih_araligini_bul(
                    fiyat_verisi
                )
            )

        except BacktestServiceError:
            raise

        except (
            ValueError,
            MarketDataError,
            StockAnalyzerError,
            HistoricalSignalGeneratorError,
            BacktestEngineError,
            PerformanceBreakdownError,
            EquityCurveError,
            BenchmarkComparisonError,
            DailyEquityCurveError,
            AnalysisContextError,
        ) as hata:
            raise BacktestServiceError(
                f"{temiz_sembol} backtest "
                f"çalıştırılamadı: {hata}"
            ) from hata

        return StockBacktestReport(
            sembol=temiz_sembol,
            fiyat_bar_sayisi=len(
                fiyat_verisi
            ),
            ilk_fiyat_tarihi=ilk_tarih,
            son_fiyat_tarihi=son_tarih,
            sinyal_uretimi=sinyal_uretimi,
            backtest_sonucu=backtest_sonucu,
            performans_dagilimi=(
                performans_dagilimi
            ),
            ozsermaye_raporu=(
                ozsermaye_raporu
            ),
            benchmark_karsilastirmasi=(
                benchmark_karsilastirmasi
            ),
            hizalanmis_benchmark_karsilastirmasi=(
                hizalanmis_benchmark_karsilastirmasi
            ),
            gunluk_ozsermaye_raporu=(
                gunluk_ozsermaye_raporu
            ),
            analiz_baglami=analiz_baglami,
        )

    def _hizalanmis_benchmark_olustur(
        self,
        fiyat_verisi: pd.DataFrame,
        backtest_sonucu: BacktestResult,
        strateji_toplam_getiri_orani: float,
        strateji_maksimum_dusus_orani: float,
        baslangic_sermayesi: float,
        islem_maliyeti_orani: float,
    ) -> BenchmarkComparisonReport | None:
        islemler = backtest_sonucu.islemler

        if not islemler:
            return None

        ilk_giris_tarihi = min(
            islem.giris_tarihi
            for islem in islemler
        )

        son_cikis_tarihi = max(
            islem.cikis_tarihi
            for islem in islemler
        )

        if son_cikis_tarihi <= ilk_giris_tarihi:
            return None

        return self._benchmark_analizcisi.analiz_et(
            fiyat_verisi=fiyat_verisi,
            strateji_toplam_getiri_orani=(
                strateji_toplam_getiri_orani
            ),
            strateji_maksimum_dusus_orani=(
                strateji_maksimum_dusus_orani
            ),
            baslangic_tarihi=ilk_giris_tarihi,
            bitis_tarihi=son_cikis_tarihi,
            baslangic_sermayesi=baslangic_sermayesi,
            islem_maliyeti_orani=islem_maliyeti_orani,
        )

    @staticmethod
    def _gorunum_secimini_bul(
        gorunumler: tuple[str, ...],
    ) -> str:
        from ..analysis.scan_filter import (
            NEGATIF_GORUNUM,
            NOTR_GORUNUM,
            POZITIF_GORUNUM,
            TUM_GORUNUMLER,
        )

        eslemeler = {
            TUM_GORUNUMLER: "tum",
            (POZITIF_GORUNUM,): "pozitif",
            (NOTR_GORUNUM,): "notr",
            (NEGATIF_GORUNUM,): "negatif",
            (POZITIF_GORUNUM, NOTR_GORUNUM): "pozitif-notr",
        }

        try:
            return eslemeler[tuple(gorunumler)]
        except KeyError as hata:
            raise BacktestServiceError(
                "Analiz profili için teknik görünüm seçimi "
                "eşlenemedi."
            ) from hata

    @staticmethod
    def _orani_yuzdeye_cevir(
        oran: float | None,
    ) -> float | None:
        if oran is None:
            return None

        return oran * 100.0

    @staticmethod
    def _sembolu_hazirla(
        sembol: str,
    ) -> str:
        temiz_sembol = sembol.strip().upper()

        if not temiz_sembol:
            raise ValueError(
                "Hisse sembolü boş olamaz."
            )

        if "." not in temiz_sembol:
            temiz_sembol += ".IS"

        return temiz_sembol

    @staticmethod
    def _tarih_araligini_bul(
        fiyat_verisi: pd.DataFrame,
    ) -> tuple[str, str]:
        tarihler = pd.to_datetime(
            fiyat_verisi.index,
            errors="coerce",
        )

        if tarihler.isna().any():
            raise BacktestServiceError(
                "Fiyat verisinde geçersiz tarihler var."
            )

        ilk_tarih = (
            tarihler.min()
            .date()
            .isoformat()
        )

        son_tarih = (
            tarihler.max()
            .date()
            .isoformat()
        )

        return ilk_tarih, son_tarih