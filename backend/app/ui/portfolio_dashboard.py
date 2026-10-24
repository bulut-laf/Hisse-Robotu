from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
import re
from typing import Callable, Protocol

import pandas as pd

from ..analysis.stock_analyzer import StockAnalyzer, StockAnalyzerError
from ..backtest.analysis_context import analiz_baglamini_olustur
from ..backtest.analysis_profile import (
    AnalysisProfile,
    ORTAK_BASLANGIC_SERMAYESI,
    ORTAK_ELDE_TUTMA_GUNU,
    ORTAK_GORUNUM_SECIMI,
    ORTAK_HEDEF_YUZDE,
    ORTAK_INDIRME_DONEMI,
    ORTAK_ISLEM_GUNU,
    ORTAK_MALIYET_YUZDE,
    ORTAK_MINIMUM_BAR,
    ORTAK_MINIMUM_SKOR,
    ORTAK_STOP_YUZDE,
    sembolu_hazirla,
)
from ..backtest.backtest_engine import BacktestEngine, BacktestEngineError
from ..backtest.backtest_models import BacktestTrade
from ..backtest.historical_signal_generator import (
    HistoricalSignalGenerator,
    HistoricalSignalGeneratorError,
)
from ..backtest.portfolio_backtest import (
    PortfolioBacktestAnalyzer,
    PortfolioBacktestConfig,
    PortfolioBacktestError,
    PortfolioBacktestReport,
)
from ..backtest.position_overlap import cakisan_islemleri_filtrele
from ..data.market_data import MarketDataError, fiyat_verisi_getir


MAKSIMUM_DASHBOARD_SEMBOLU = 10


class PortfolioDashboardError(RuntimeError):
    """Portföy paneli için kullanıcıya gösterilebilir çalışma hatası."""


def sembolleri_hazirla(
    semboller: str | tuple[str, ...] | list[str],
) -> tuple[str, ...]:
    """Virgül, noktalı virgül veya boşlukla ayrılan sembolleri normalize eder."""

    if isinstance(semboller, str):
        ham_semboller = re.split(r"[,;\s]+", semboller.strip())
    else:
        ham_semboller = list(semboller)

    hazir = tuple(
        dict.fromkeys(
            sembolu_hazirla(str(sembol))
            for sembol in ham_semboller
            if str(sembol).strip()
        )
    )

    if len(hazir) < 2:
        raise ValueError("Portföy backtest’i için en az iki hisse gereklidir.")

    if len(hazir) > MAKSIMUM_DASHBOARD_SEMBOLU:
        raise ValueError(
            "Portföy panelinde en fazla "
            f"{MAKSIMUM_DASHBOARD_SEMBOLU} hisse kullanılabilir."
        )

    return hazir


@dataclass(frozen=True)
class PortfolioDashboardRequest:
    """Tarayıcı formundan alınan çoklu hisse portföy ayarları."""

    semboller: str | tuple[str, ...] = "THYAO, TUPRS, ASELS"
    islem_gunu: int = ORTAK_ISLEM_GUNU
    indirme_donemi: str = ORTAK_INDIRME_DONEMI
    minimum_bar_sayisi: int = ORTAK_MINIMUM_BAR
    gorunum_secimi: str = ORTAK_GORUNUM_SECIMI
    elde_tutma_gunu: int = ORTAK_ELDE_TUTMA_GUNU
    minimum_skor: int = ORTAK_MINIMUM_SKOR
    baslangic_sermayesi: float = ORTAK_BASLANGIC_SERMAYESI
    maliyet_yuzde: float = ORTAK_MALIYET_YUZDE
    stop_yuzde: float | None = ORTAK_STOP_YUZDE
    hedef_yuzde: float | None = ORTAK_HEDEF_YUZDE
    maksimum_es_zamanli_pozisyon: int = 3

    def __post_init__(self) -> None:
        hazir_semboller = sembolleri_hazirla(self.semboller)
        object.__setattr__(self, "semboller", hazir_semboller)

        if self.maksimum_es_zamanli_pozisyon <= 0:
            raise ValueError(
                "Maksimum eş zamanlı pozisyon sayısı pozitif olmalıdır."
            )
        if self.maksimum_es_zamanli_pozisyon > len(hazir_semboller):
            raise ValueError(
                "Maksimum eş zamanlı pozisyon sayısı hisse sayısını aşamaz."
            )

        # Veri, sinyal ve tek-hisse işlemleri ortak profil ile doğrulanır.
        self.profil_olustur()
        self.portfoy_yapilandirmasi()

    def profil_olustur(self) -> AnalysisProfile:
        return AnalysisProfile(
            islem_gunu=self.islem_gunu,
            indirme_donemi=self.indirme_donemi,
            minimum_bar_sayisi=self.minimum_bar_sayisi,
            gorunum_secimi=self.gorunum_secimi,
            elde_tutma_gunu=self.elde_tutma_gunu,
            minimum_skor=self.minimum_skor,
            baslangic_sermayesi=self.baslangic_sermayesi,
            pozisyon_yuzde=100.0,
            maliyet_yuzde=self.maliyet_yuzde,
            stop_yuzde=self.stop_yuzde,
            hedef_yuzde=self.hedef_yuzde,
        )

    def portfoy_yapilandirmasi(self) -> PortfolioBacktestConfig:
        return PortfolioBacktestConfig(
            baslangic_sermayesi=self.baslangic_sermayesi,
            maksimum_es_zamanli_pozisyon=(
                self.maksimum_es_zamanli_pozisyon
            ),
            pozisyon_basina_sermaye_orani=None,
            islem_maliyeti_orani=self.maliyet_yuzde / 100.0,
            zarar_durdur_orani=(
                None
                if self.stop_yuzde is None
                else self.stop_yuzde / 100.0
            ),
        )


@dataclass(frozen=True)
class PreparedPortfolioSymbol:
    """Tek sembolün portföy simülasyonuna hazır fiyat ve işlem havuzu."""

    sembol: str
    fiyat_verisi: pd.DataFrame
    veri_kimligi: str
    islemler: tuple[BacktestTrade, ...]


@dataclass(frozen=True)
class PortfolioDashboardSummary:
    """Portföy panelindeki sonuç kartları için özet."""

    semboller: tuple[str, ...]
    portfoy_donemi: str
    ayar_kimligi: str
    portfoy_veri_kimligi: str
    tamamlanan_islem_sayisi: int
    atlanan_islem_sayisi: int
    bitis_sermayesi: float
    toplam_getiri_yuzde: float
    maksimum_dusus_yuzde: float
    guncel_dusus_yuzde: float
    kar_faktoru: float | None
    gerceklesen_maksimum_pozisyon: int
    ortalama_sermaye_kullanim_yuzde: float
    maksimum_sermaye_kullanim_yuzde: float


@dataclass(frozen=True)
class PortfolioContributionRow:
    """Hisse bazlı katkı tablosundaki tek satır."""

    sembol: str
    islem_sayisi: int
    kazanma_yuzde: float
    toplam_ayrilan_sermaye: float
    net_kar: float
    baslangica_katki_yuzde: float

    def kayit(self) -> dict[str, object]:
        return {
            "Sembol": self.sembol,
            "İşlem": self.islem_sayisi,
            "Kazanma (%)": self.kazanma_yuzde,
            "Toplam Ayrılan Sermaye": self.toplam_ayrilan_sermaye,
            "Net Kâr": self.net_kar,
            "Başlangıca Katkı (%)": self.baslangica_katki_yuzde,
        }

    def kompakt_kayit(self) -> dict[str, object]:
        """Dar ekranlarda gösterilecek temel katkı alanlarını döndürür."""

        return {
            "Sembol": self.sembol,
            "İşlem": self.islem_sayisi,
            "Kazanma (%)": self.kazanma_yuzde,
            "Net Kâr": self.net_kar,
            "Katkı (%)": self.baslangica_katki_yuzde,
        }

    def hacim_kaydi(self) -> dict[str, object]:
        """Kümülatif ayrılan sermayeyi ayrı ayrıntı tablosuna taşır."""

        return {
            "Sembol": self.sembol,
            "Toplam Ayrılan Sermaye": self.toplam_ayrilan_sermaye,
        }


@dataclass(frozen=True)
class PortfolioEquityRow:
    """Portföy günlük özsermaye grafiği için tek nokta."""

    tarih: str
    ozsermaye: float
    dusus_yuzde: float
    acik_pozisyon_sayisi: int
    sermaye_kullanim_yuzde: float

    def kayit(self) -> dict[str, object]:
        return {
            "Tarih": self.tarih,
            "Özsermaye": self.ozsermaye,
            "Düşüş (%)": self.dusus_yuzde,
            "Açık Pozisyon": self.acik_pozisyon_sayisi,
            "Sermaye Kullanımı (%)": self.sermaye_kullanim_yuzde,
        }


@dataclass(frozen=True)
class PortfolioSkippedReasonRow:
    """Portföy tarafından atlanan işlemlerin neden özeti."""

    neden: str
    adet: int

    def kayit(self) -> dict[str, object]:
        return {"Neden": self.neden, "Adet": self.adet}


@dataclass(frozen=True)
class PortfolioDashboardResult:
    """Streamlit portföy ekranına sunulan tamamlanmış sonuç."""

    ozet: PortfolioDashboardSummary
    katkilar: tuple[PortfolioContributionRow, ...]
    gunluk_ozsermaye: tuple[PortfolioEquityRow, ...]
    atlanma_nedenleri: tuple[PortfolioSkippedReasonRow, ...]

    def katki_kayitlari(self) -> list[dict[str, object]]:
        return [satir.kayit() for satir in self.katkilar]

    def kompakt_katki_kayitlari(self) -> list[dict[str, object]]:
        return [satir.kompakt_kayit() for satir in self.katkilar]

    def hacim_kayitlari(self) -> list[dict[str, object]]:
        return [satir.hacim_kaydi() for satir in self.katkilar]

    def ozsermaye_kayitlari(self) -> list[dict[str, object]]:
        return [satir.kayit() for satir in self.gunluk_ozsermaye]

    def atlanma_kayitlari(self) -> list[dict[str, object]]:
        return [satir.kayit() for satir in self.atlanma_nedenleri]


def ozsermaye_eksen_araligi(
    kayitlar: list[dict[str, object]],
) -> tuple[float, float] | None:
    """Pozitif özsermaye grafiği için negatif boşluk üretmeyen Y aralığı."""

    degerler = [
        float(kayit["Özsermaye"])
        for kayit in kayitlar
        if kayit.get("Özsermaye") is not None
    ]
    if not degerler:
        return None

    en_dusuk = min(degerler)
    en_yuksek = max(degerler)
    yayilim = en_yuksek - en_dusuk
    tampon = yayilim * 0.05
    if tampon <= 0.0:
        tampon = max(abs(en_yuksek) * 0.05, 1.0)

    alt_sinir = en_dusuk - tampon
    if en_dusuk >= 0.0:
        alt_sinir = max(0.0, alt_sinir)

    return alt_sinir, en_yuksek + tampon


class PortfolioAnalyzerProtocol(Protocol):
    def analiz_et(
        self,
        fiyat_verileri: dict[str, pd.DataFrame],
        islemler: tuple[BacktestTrade, ...],
        yapilandirma: PortfolioBacktestConfig | None = None,
    ) -> PortfolioBacktestReport:
        ...


SymbolPreparer = Callable[
    [str, AnalysisProfile],
    PreparedPortfolioSymbol,
]


class PortfolioDashboardService:
    """Mevcut portföy motorunu tarayıcı arayüzü modeline dönüştürür."""

    def __init__(
        self,
        sembol_hazirlayici: SymbolPreparer | None = None,
        portfoy_analizcisi: PortfolioAnalyzerProtocol | None = None,
    ) -> None:
        self._sembol_hazirlayici = (
            sembol_hazirlayici
            if sembol_hazirlayici is not None
            else self._varsayilan_sembol_hazirla
        )
        self._portfoy_analizcisi = (
            portfoy_analizcisi
            if portfoy_analizcisi is not None
            else PortfolioBacktestAnalyzer()
        )

    def calistir(
        self,
        istek: PortfolioDashboardRequest,
    ) -> PortfolioDashboardResult:
        if not isinstance(istek, PortfolioDashboardRequest):
            raise TypeError(
                "Arayüz isteği PortfolioDashboardRequest olmalıdır."
            )

        profil = istek.profil_olustur()
        hazir_semboller: list[PreparedPortfolioSymbol] = []

        for sembol in istek.semboller:
            try:
                hazir_semboller.append(
                    self._sembol_hazirlayici(sembol, profil)
                )
            except (
                ValueError,
                MarketDataError,
                StockAnalyzerError,
                HistoricalSignalGeneratorError,
                BacktestEngineError,
            ) as hata:
                raise PortfolioDashboardError(
                    f"{sembol} hazırlanamadı: {hata}"
                ) from hata

        fiyat_verileri = {
            hazir.sembol: hazir.fiyat_verisi
            for hazir in hazir_semboller
        }
        islemler = tuple(
            islem
            for hazir in hazir_semboller
            for islem in hazir.islemler
        )

        try:
            rapor = self._portfoy_analizcisi.analiz_et(
                fiyat_verileri=fiyat_verileri,
                islemler=islemler,
                yapilandirma=istek.portfoy_yapilandirmasi(),
            )
        except (ValueError, PortfolioBacktestError) as hata:
            raise PortfolioDashboardError(
                f"Portföy backtest’i tamamlanamadı: {hata}"
            ) from hata

        veri_kimlikleri = {
            hazir.sembol: hazir.veri_kimligi
            for hazir in hazir_semboller
        }

        return PortfolioDashboardResult(
            ozet=self._ozet_olustur(
                rapor=rapor,
                semboller=tuple(istek.semboller),
                ayar_kimligi=profil.ayar_kimligi,
                veri_kimlikleri=veri_kimlikleri,
            ),
            katkilar=self._katkilari_olustur(rapor),
            gunluk_ozsermaye=self._ozsermayeyi_olustur(rapor),
            atlanma_nedenleri=self._atlanma_nedenlerini_olustur(rapor),
        )

    @staticmethod
    def _varsayilan_sembol_hazirla(
        sembol: str,
        profil: AnalysisProfile,
    ) -> PreparedPortfolioSymbol:
        fiyat_verisi = fiyat_verisi_getir(
            sembol=sembol,
            islem_gunu=profil.islem_gunu,
            indirme_donemi=profil.indirme_donemi,
            yalnizca_tamamlanmis_gunler=True,
        )
        baglam = analiz_baglamini_olustur(
            fiyat_verisi=fiyat_verisi,
            profil=profil,
        )
        analizci = StockAnalyzer()
        sinyal_uretimi = HistoricalSignalGenerator(
            analizci.veriden_analiz_et
        ).uret(
            sembol=sembol,
            fiyat_verisi=fiyat_verisi,
            yapilandirma=profil.sinyal_yapilandirmasi(),
        )
        tek_hisse_ayarlari = profil.backtest_yapilandirmasi()
        ham_sonuc = BacktestEngine().calistir(
            veriler={sembol: fiyat_verisi},
            sinyaller=sinyal_uretimi.sinyaller,
            yapilandirma=tek_hisse_ayarlari,
        )
        sonuc = cakisan_islemleri_filtrele(
            sonuc=ham_sonuc,
            yapilandirma=tek_hisse_ayarlari,
        )

        return PreparedPortfolioSymbol(
            sembol=sembol,
            fiyat_verisi=fiyat_verisi,
            veri_kimligi=baglam.veri_kimligi,
            islemler=tuple(sonuc.islemler),
        )

    @staticmethod
    def _portfoy_veri_kimligi(
        veri_kimlikleri: dict[str, str],
    ) -> str:
        icerik = "|".join(
            f"{sembol}:{veri_kimlikleri[sembol]}"
            for sembol in sorted(veri_kimlikleri)
        ).encode("utf-8")
        return sha256(icerik).hexdigest()[:12]

    @classmethod
    def _ozet_olustur(
        cls,
        rapor: PortfolioBacktestReport,
        semboller: tuple[str, ...],
        ayar_kimligi: str,
        veri_kimlikleri: dict[str, str],
    ) -> PortfolioDashboardSummary:
        return PortfolioDashboardSummary(
            semboller=semboller,
            portfoy_donemi=f"{rapor.ilk_tarih or '-'} — {rapor.son_tarih or '-'}",
            ayar_kimligi=ayar_kimligi,
            portfoy_veri_kimligi=cls._portfoy_veri_kimligi(
                veri_kimlikleri
            ),
            tamamlanan_islem_sayisi=rapor.tamamlanan_islem_sayisi,
            atlanan_islem_sayisi=rapor.atlanan_islem_sayisi,
            bitis_sermayesi=rapor.bitis_sermayesi,
            toplam_getiri_yuzde=rapor.toplam_getiri_orani * 100.0,
            maksimum_dusus_yuzde=rapor.maksimum_dusus_orani * 100.0,
            guncel_dusus_yuzde=rapor.guncel_dusus_orani * 100.0,
            kar_faktoru=rapor.kar_faktoru,
            gerceklesen_maksimum_pozisyon=(
                rapor.maksimum_es_zamanli_pozisyon
            ),
            ortalama_sermaye_kullanim_yuzde=(
                rapor.ortalama_sermaye_kullanim_orani * 100.0
            ),
            maksimum_sermaye_kullanim_yuzde=(
                rapor.maksimum_sermaye_kullanim_orani * 100.0
            ),
        )

    @staticmethod
    def _katkilari_olustur(
        rapor: PortfolioBacktestReport,
    ) -> tuple[PortfolioContributionRow, ...]:
        return tuple(
            PortfolioContributionRow(
                sembol=katki.sembol,
                islem_sayisi=katki.islem_sayisi,
                kazanma_yuzde=katki.kazanma_orani * 100.0,
                toplam_ayrilan_sermaye=katki.toplam_ayrilan_sermaye,
                net_kar=katki.net_kar,
                baslangica_katki_yuzde=(
                    katki.baslangic_sermayesine_katki_orani * 100.0
                ),
            )
            for katki in rapor.sembol_katkilari
        )

    @staticmethod
    def _ozsermayeyi_olustur(
        rapor: PortfolioBacktestReport,
    ) -> tuple[PortfolioEquityRow, ...]:
        return tuple(
            PortfolioEquityRow(
                tarih=nokta.tarih.isoformat(),
                ozsermaye=nokta.ozsermaye,
                dusus_yuzde=nokta.dusus_orani * 100.0,
                acik_pozisyon_sayisi=nokta.acik_pozisyon_sayisi,
                sermaye_kullanim_yuzde=(
                    nokta.sermaye_kullanim_orani * 100.0
                ),
            )
            for nokta in rapor.gunluk_noktalar
        )

    @staticmethod
    def _atlanma_nedenlerini_olustur(
        rapor: PortfolioBacktestReport,
    ) -> tuple[PortfolioSkippedReasonRow, ...]:
        sayilar = Counter(
            atlanan.neden for atlanan in rapor.atlanan_islemler
        )
        return tuple(
            PortfolioSkippedReasonRow(neden=neden, adet=adet)
            for neden, adet in sorted(sayilar.items())
        )
