from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

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
    ORTAK_POZISYON_YUZDE,
    ORTAK_STOP_YUZDE,
    sembolu_hazirla,
)
from ..backtest.backtest_service import (
    BacktestServiceConfig,
    StockBacktestReport,
    StockBacktestService,
)


@dataclass(frozen=True)
class DashboardBacktestRequest:
    """Tarayıcı formundan alınan tek-hisse backtest ayarları."""

    sembol: str = "THYAO.IS"
    islem_gunu: int = ORTAK_ISLEM_GUNU
    indirme_donemi: str = ORTAK_INDIRME_DONEMI
    minimum_bar_sayisi: int = ORTAK_MINIMUM_BAR
    gorunum_secimi: str = ORTAK_GORUNUM_SECIMI
    elde_tutma_gunu: int = ORTAK_ELDE_TUTMA_GUNU
    minimum_skor: int = ORTAK_MINIMUM_SKOR
    baslangic_sermayesi: float = ORTAK_BASLANGIC_SERMAYESI
    pozisyon_yuzde: float = ORTAK_POZISYON_YUZDE
    maliyet_yuzde: float = ORTAK_MALIYET_YUZDE
    stop_yuzde: float | None = ORTAK_STOP_YUZDE
    hedef_yuzde: float | None = ORTAK_HEDEF_YUZDE

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "sembol",
            sembolu_hazirla(self.sembol),
        )

        # Bütün doğrulamalar ortak profil üzerinden yürütülür.
        self.profil_olustur()

    def profil_olustur(self) -> AnalysisProfile:
        return AnalysisProfile(
            islem_gunu=self.islem_gunu,
            indirme_donemi=self.indirme_donemi,
            minimum_bar_sayisi=self.minimum_bar_sayisi,
            gorunum_secimi=self.gorunum_secimi,
            elde_tutma_gunu=self.elde_tutma_gunu,
            minimum_skor=self.minimum_skor,
            baslangic_sermayesi=self.baslangic_sermayesi,
            pozisyon_yuzde=self.pozisyon_yuzde,
            maliyet_yuzde=self.maliyet_yuzde,
            stop_yuzde=self.stop_yuzde,
            hedef_yuzde=self.hedef_yuzde,
        )

    def servis_yapilandirmasi(self) -> BacktestServiceConfig:
        profil = self.profil_olustur()

        return BacktestServiceConfig(
            islem_gunu=profil.islem_gunu,
            indirme_donemi=profil.indirme_donemi,
            yalnizca_tamamlanmis_gunler=True,
            pozisyon_cakismalarini_engelle=True,
            sinyal_ayarlari=profil.sinyal_yapilandirmasi(),
            backtest_ayarlari=profil.backtest_yapilandirmasi(),
        )


@dataclass(frozen=True)
class DashboardSummary:
    """Arayüzdeki sonuç kartlarında gösterilecek özet."""

    sembol: str
    fiyat_donemi: str
    fiyat_bar_sayisi: int
    analiz_kimligi: str
    veri_kimligi: str
    ayar_kimligi: str
    tamamlanan_islem_sayisi: int
    atlanan_sinyal_sayisi: int
    kazanma_yuzde: float
    toplam_getiri_yuzde: float
    bitis_sermayesi: float
    maksimum_dusus_yuzde: float
    guncel_dusus_yuzde: float
    kar_faktoru: float | None
    al_tut_getiri_yuzde: float | None


@dataclass(frozen=True)
class DashboardTradeRow:
    """İşlem tablosundaki tek satır."""

    sira: int
    sinyal_tarihi: str
    giris_tarihi: str
    cikis_tarihi: str
    skor: int
    giris_fiyati: float
    cikis_fiyati: float
    net_getiri_yuzde: float
    elde_tutulan_bar: int
    cikis_nedeni: str

    def kayit(self) -> dict[str, object]:
        return {
            "No": self.sira,
            "Sinyal": self.sinyal_tarihi,
            "Giriş": self.giris_tarihi,
            "Çıkış": self.cikis_tarihi,
            "Skor": self.skor,
            "Giriş Fiyatı": self.giris_fiyati,
            "Çıkış Fiyatı": self.cikis_fiyati,
            "Net Getiri (%)": self.net_getiri_yuzde,
            "Bar": self.elde_tutulan_bar,
            "Çıkış Nedeni": self.cikis_nedeni,
        }


@dataclass(frozen=True)
class DashboardResult:
    """Tarayıcı arayüzüne sunulan tamamlanmış sonuç."""

    ozet: DashboardSummary
    islemler: tuple[DashboardTradeRow, ...]

    def islem_kayitlari(self) -> list[dict[str, object]]:
        return [islem.kayit() for islem in self.islemler]


class BacktestServiceProtocol(Protocol):
    def calistir(
        self,
        sembol: str,
        yapilandirma: BacktestServiceConfig | None = None,
    ) -> StockBacktestReport:
        ...


class BacktestDashboardService:
    """Mevcut backtest servisini arayüz modeline dönüştürür."""

    def __init__(
        self,
        backtest_servisi: BacktestServiceProtocol | None = None,
    ) -> None:
        self._backtest_servisi = (
            backtest_servisi
            if backtest_servisi is not None
            else StockBacktestService()
        )

    def calistir(
        self,
        istek: DashboardBacktestRequest,
    ) -> DashboardResult:
        if not isinstance(istek, DashboardBacktestRequest):
            raise TypeError(
                "Arayüz isteği DashboardBacktestRequest olmalıdır."
            )

        rapor = self._backtest_servisi.calistir(
            sembol=istek.sembol,
            yapilandirma=istek.servis_yapilandirmasi(),
        )

        return DashboardResult(
            ozet=self._ozet_olustur(rapor),
            islemler=self._islemleri_olustur(rapor),
        )

    @staticmethod
    def _ozet_olustur(
        rapor: StockBacktestReport,
    ) -> DashboardSummary:
        metrikler = rapor.backtest_sonucu.metrikler
        gunluk = rapor.gunluk_ozsermaye_raporu
        baglam = rapor.analiz_baglami
        hizalanmis = rapor.hizalanmis_benchmark_karsilastirmasi

        maksimum_dusus_orani = (
            gunluk.maksimum_dusus_orani
            if gunluk is not None
            else rapor.ozsermaye_raporu.maksimum_dusus_orani
        )
        guncel_dusus_orani = (
            gunluk.guncel_dusus_orani
            if gunluk is not None
            else 0.0
        )
        al_tut_getiri_orani = (
            hizalanmis.al_tut.net_getiri_orani
            if hizalanmis is not None
            else None
        )

        return DashboardSummary(
            sembol=rapor.sembol,
            fiyat_donemi=(
                f"{rapor.ilk_fiyat_tarihi} — "
                f"{rapor.son_fiyat_tarihi}"
            ),
            fiyat_bar_sayisi=rapor.fiyat_bar_sayisi,
            analiz_kimligi=(
                baglam.analiz_kimligi if baglam is not None else "-"
            ),
            veri_kimligi=(
                baglam.veri_kimligi if baglam is not None else "-"
            ),
            ayar_kimligi=(
                baglam.ayar_kimligi if baglam is not None else "-"
            ),
            tamamlanan_islem_sayisi=(
                rapor.backtest_sonucu.tamamlanan_islem_sayisi
            ),
            atlanan_sinyal_sayisi=(
                rapor.backtest_sonucu.atlanan_sinyal_sayisi
            ),
            kazanma_yuzde=metrikler.kazanma_orani * 100.0,
            toplam_getiri_yuzde=(
                rapor.ozsermaye_raporu
                .toplam_bilesik_getiri_orani
                * 100.0
            ),
            bitis_sermayesi=rapor.ozsermaye_raporu.bitis_sermayesi,
            maksimum_dusus_yuzde=maksimum_dusus_orani * 100.0,
            guncel_dusus_yuzde=guncel_dusus_orani * 100.0,
            kar_faktoru=metrikler.kar_faktoru,
            al_tut_getiri_yuzde=(
                al_tut_getiri_orani * 100.0
                if al_tut_getiri_orani is not None
                else None
            ),
        )

    @staticmethod
    def _islemleri_olustur(
        rapor: StockBacktestReport,
    ) -> tuple[DashboardTradeRow, ...]:
        return tuple(
            DashboardTradeRow(
                sira=sira,
                sinyal_tarihi=islem.sinyal_tarihi.isoformat(),
                giris_tarihi=islem.giris_tarihi.isoformat(),
                cikis_tarihi=islem.cikis_tarihi.isoformat(),
                skor=islem.skor,
                giris_fiyati=islem.giris_fiyati,
                cikis_fiyati=islem.cikis_fiyati,
                net_getiri_yuzde=(
                    islem.net_getiri_orani * 100.0
                ),
                elde_tutulan_bar=islem.elde_tutulan_bar,
                cikis_nedeni=islem.cikis_nedeni,
            )
            for sira, islem in enumerate(
                rapor.backtest_sonucu.islemler,
                start=1,
            )
        )
