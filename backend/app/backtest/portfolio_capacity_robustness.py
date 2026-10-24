from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isclose
from statistics import median
from typing import Iterable, Mapping, Sequence

import pandas as pd

from .backtest_models import BacktestTrade
from .portfolio_capacity_sensitivity import (
    PortfolioCapacityScenario,
    PortfolioCapacitySensitivityAnalyzer,
    PortfolioCapacitySensitivityReport,
)


PIYASA_GUCLU = "Güçlü"
PIYASA_ZAYIF = "Zayıf"
PIYASA_NOTR = "Nötr"


class PortfolioCapacityRobustnessError(ValueError):
    """Portföy kapasitesi sağlamlık analizi girdileri geçersizdir."""


@dataclass(frozen=True)
class RollingCapacityWindow:
    """Tek bir kayan zaman penceresindeki kapasite karşılaştırması."""

    baslangic_tarihi: date
    bitis_tarihi: date
    piyasa_getiri_orani: float
    piyasa_grubu: str
    aday_islem_sayisi: int
    kapasite_raporu: PortfolioCapacitySensitivityReport

    @property
    def getiri_lideri(self) -> int | None:
        senaryo = self.kapasite_raporu.en_yuksek_getiri_senaryosu
        return None if senaryo is None else senaryo.kapasite

    @property
    def getiri_dusus_lideri(self) -> int | None:
        senaryo = self.kapasite_raporu.en_iyi_getiri_dusus_senaryosu
        return None if senaryo is None else senaryo.kapasite


@dataclass(frozen=True)
class CapacityWindowSummary:
    """Bir kapasitenin tüm yeterli kayan pencerelerdeki özeti."""

    kapasite: int
    pencere_sayisi: int
    pozitif_pencere_sayisi: int
    getiri_liderligi_sayisi: int
    getiri_dusus_liderligi_sayisi: int
    medyan_getiri_orani: float
    medyan_maksimum_dusus_orani: float
    medyan_getiri_dusus_orani: float | None

    @property
    def pozitif_pencere_orani(self) -> float:
        if self.pencere_sayisi == 0:
            return 0.0
        return self.pozitif_pencere_sayisi / self.pencere_sayisi


@dataclass(frozen=True)
class LeaveOneOutScenario:
    """Tam sepet veya bir sembol dışarıda bırakılarak hesaplanan sonuç."""

    dislanan_sembol: str | None
    dahil_semboller: tuple[str, ...]
    aday_islem_sayisi: int
    kapasite_raporu: PortfolioCapacitySensitivityReport

    @property
    def getiri_lideri(self) -> int | None:
        senaryo = self.kapasite_raporu.en_yuksek_getiri_senaryosu
        return None if senaryo is None else senaryo.kapasite

    @property
    def getiri_dusus_lideri(self) -> int | None:
        senaryo = self.kapasite_raporu.en_iyi_getiri_dusus_senaryosu
        return None if senaryo is None else senaryo.kapasite


@dataclass(frozen=True)
class PortfolioCapacityRobustnessReport:
    """Kayan pencere ve sembol dışlama sağlamlık sonuçları."""

    pencereler: tuple[RollingCapacityWindow, ...]
    kapasite_ozetleri: tuple[CapacityWindowSummary, ...]
    sembol_dislamalari: tuple[LeaveOneOutScenario, ...]
    piyasa_getiri_medyan_orani: float | None
    pencere_bar_sayisi: int
    adim_bar_sayisi: int
    minimum_islem_sayisi: int

    def kapasite_ozeti(self, kapasite: int) -> CapacityWindowSummary | None:
        return next(
            (
                ozet
                for ozet in self.kapasite_ozetleri
                if ozet.kapasite == kapasite
            ),
            None,
        )


class PortfolioCapacityRobustnessAnalyzer:
    """
    Portföy kapasitesini farklı zaman pencerelerinde ve sembol
    bileşimlerinde karşılaştırır.

    Piyasa grubu bir işlem filtresi değildir. Her kayan pencerenin
    eşit ağırlıklı gerçekleşmiş fiyat getirisi, yeterli pencerelerin
    medyanıyla karşılaştırılarak yalnızca açıklama amacıyla Güçlü,
    Zayıf veya Nötr olarak etiketlenir.
    """

    def __init__(
        self,
        kapasite_analizcisi: PortfolioCapacitySensitivityAnalyzer | None = None,
    ) -> None:
        self._kapasite_analizcisi = (
            kapasite_analizcisi
            if kapasite_analizcisi is not None
            else PortfolioCapacitySensitivityAnalyzer()
        )

    def analiz_et(
        self,
        fiyat_verileri: Mapping[str, pd.DataFrame],
        islemler: Iterable[BacktestTrade],
        kapasiteler: Sequence[int] = (1, 2, 3),
        pencere_bar_sayisi: int = 252,
        adim_bar_sayisi: int = 63,
        minimum_islem_sayisi: int = 10,
        baslangic_sermayesi: float = 100_000.0,
        islem_maliyeti_orani: float = 0.001,
    ) -> PortfolioCapacityRobustnessReport:
        self._pozitif_tam_sayi_dogrula(
            pencere_bar_sayisi,
            "Pencere bar sayısı",
        )
        self._pozitif_tam_sayi_dogrula(
            adim_bar_sayisi,
            "Adım bar sayısı",
        )
        self._pozitif_tam_sayi_dogrula(
            minimum_islem_sayisi,
            "Minimum işlem sayısı",
        )

        hazir_veriler = self._fiyat_verilerini_hazirla(fiyat_verileri)
        hazir_islemler = tuple(islemler)
        takvim = self._ortak_takvimi_olustur(hazir_veriler)

        ham_pencereler: list[
            tuple[
                date,
                date,
                float,
                int,
                PortfolioCapacitySensitivityReport,
            ]
        ] = []

        for baslangic_indeksi in self._pencere_baslangic_indeksleri(
            toplam_bar=len(takvim),
            pencere_bar_sayisi=pencere_bar_sayisi,
            adim_bar_sayisi=adim_bar_sayisi,
        ):
            pencere_tarihleri = takvim[
                baslangic_indeksi : baslangic_indeksi + pencere_bar_sayisi
            ]
            baslangic = pencere_tarihleri[0]
            bitis = pencere_tarihleri[-1]
            pencere_islemleri = tuple(
                islem
                for islem in hazir_islemler
                if islem.giris_tarihi >= baslangic
                and islem.cikis_tarihi <= bitis
            )

            if len(pencere_islemleri) < minimum_islem_sayisi:
                continue

            pencere_verileri = self._tarih_araligina_kirp(
                fiyat_verileri=hazir_veriler,
                baslangic=baslangic,
                bitis=bitis,
            )
            kapasite_raporu = self._kapasite_analizcisi.analiz_et(
                fiyat_verileri=pencere_verileri,
                islemler=pencere_islemleri,
                kapasiteler=kapasiteler,
                baslangic_sermayesi=baslangic_sermayesi,
                islem_maliyeti_orani=islem_maliyeti_orani,
            )
            piyasa_getirisi = self._esit_agirlikli_piyasa_getirisi(
                pencere_verileri
            )
            ham_pencereler.append(
                (
                    baslangic,
                    bitis,
                    piyasa_getirisi,
                    len(pencere_islemleri),
                    kapasite_raporu,
                )
            )

        piyasa_medyan = (
            median(pencere[2] for pencere in ham_pencereler)
            if ham_pencereler
            else None
        )
        pencereler = tuple(
            RollingCapacityWindow(
                baslangic_tarihi=baslangic,
                bitis_tarihi=bitis,
                piyasa_getiri_orani=piyasa_getirisi,
                piyasa_grubu=self._piyasa_grubunu_belirle(
                    piyasa_getirisi,
                    piyasa_medyan,
                ),
                aday_islem_sayisi=aday_islem_sayisi,
                kapasite_raporu=kapasite_raporu,
            )
            for (
                baslangic,
                bitis,
                piyasa_getirisi,
                aday_islem_sayisi,
                kapasite_raporu,
            ) in ham_pencereler
        )

        kapasite_ozetleri = self._kapasite_ozetlerini_olustur(
            pencereler=pencereler,
            kapasiteler=kapasiteler,
        )
        sembol_dislamalari = self._sembol_dislamalarini_olustur(
            fiyat_verileri=hazir_veriler,
            islemler=hazir_islemler,
            kapasiteler=kapasiteler,
            baslangic_sermayesi=baslangic_sermayesi,
            islem_maliyeti_orani=islem_maliyeti_orani,
        )

        return PortfolioCapacityRobustnessReport(
            pencereler=pencereler,
            kapasite_ozetleri=kapasite_ozetleri,
            sembol_dislamalari=sembol_dislamalari,
            piyasa_getiri_medyan_orani=piyasa_medyan,
            pencere_bar_sayisi=pencere_bar_sayisi,
            adim_bar_sayisi=adim_bar_sayisi,
            minimum_islem_sayisi=minimum_islem_sayisi,
        )

    @staticmethod
    def _pozitif_tam_sayi_dogrula(deger: int, ad: str) -> None:
        if isinstance(deger, bool) or not isinstance(deger, int) or deger <= 0:
            raise PortfolioCapacityRobustnessError(
                f"{ad} pozitif tam sayı olmalıdır."
            )

    @staticmethod
    def _fiyat_verilerini_hazirla(
        fiyat_verileri: Mapping[str, pd.DataFrame],
    ) -> dict[str, pd.DataFrame]:
        if not isinstance(fiyat_verileri, Mapping) or not fiyat_verileri:
            raise PortfolioCapacityRobustnessError(
                "En az bir sembole ait fiyat verisi verilmelidir."
            )

        sonuc: dict[str, pd.DataFrame] = {}
        for ham_sembol, ham_veri in fiyat_verileri.items():
            sembol = str(ham_sembol).strip().upper()
            if not sembol:
                raise PortfolioCapacityRobustnessError(
                    "Fiyat verisi sembolü boş olamaz."
                )
            if not isinstance(ham_veri, pd.DataFrame) or ham_veri.empty:
                raise PortfolioCapacityRobustnessError(
                    f"{sembol} fiyat verisi boş olmayan DataFrame olmalıdır."
                )
            if "Close" not in ham_veri.columns:
                raise PortfolioCapacityRobustnessError(
                    f"{sembol} fiyat verisinde Close sütunu bulunmalıdır."
                )

            veri = ham_veri.copy()
            tarihler = pd.to_datetime(veri.index, errors="coerce")
            if tarihler.isna().any():
                raise PortfolioCapacityRobustnessError(
                    f"{sembol} fiyat verisinde geçersiz tarih var."
                )
            if tarihler.tz is not None:
                tarihler = tarihler.tz_localize(None)
            veri.index = tarihler.normalize()
            veri = veri.sort_index()
            veri = veri.loc[~veri.index.duplicated(keep="last")]
            veri["Close"] = pd.to_numeric(veri["Close"], errors="coerce")
            if veri["Close"].isna().any() or (veri["Close"] <= 0).any():
                raise PortfolioCapacityRobustnessError(
                    f"{sembol} Close değerleri pozitif ve sayısal olmalıdır."
                )
            sonuc[sembol] = veri

        return sonuc

    @staticmethod
    def _ortak_takvimi_olustur(
        fiyat_verileri: Mapping[str, pd.DataFrame],
    ) -> tuple[date, ...]:
        tarihler = sorted(
            {
                zaman.date()
                for veri in fiyat_verileri.values()
                for zaman in veri.index
            }
        )
        if not tarihler:
            raise PortfolioCapacityRobustnessError(
                "Fiyat verilerinde işlem tarihi bulunamadı."
            )
        return tuple(tarihler)

    @staticmethod
    def _pencere_baslangic_indeksleri(
        toplam_bar: int,
        pencere_bar_sayisi: int,
        adim_bar_sayisi: int,
    ) -> tuple[int, ...]:
        if toplam_bar < pencere_bar_sayisi:
            return ()

        son_baslangic = toplam_bar - pencere_bar_sayisi
        indeksler = list(range(0, son_baslangic + 1, adim_bar_sayisi))
        if indeksler[-1] != son_baslangic:
            indeksler.append(son_baslangic)
        return tuple(indeksler)

    @staticmethod
    def _tarih_araligina_kirp(
        fiyat_verileri: Mapping[str, pd.DataFrame],
        baslangic: date,
        bitis: date,
    ) -> dict[str, pd.DataFrame]:
        sonuc: dict[str, pd.DataFrame] = {}
        baslangic_ts = pd.Timestamp(baslangic)
        bitis_ts = pd.Timestamp(bitis)

        for sembol, veri in fiyat_verileri.items():
            kirpilmis = veri.loc[
                (veri.index >= baslangic_ts) & (veri.index <= bitis_ts)
            ].copy()
            if not kirpilmis.empty:
                sonuc[sembol] = kirpilmis

        return sonuc

    @staticmethod
    def _esit_agirlikli_piyasa_getirisi(
        fiyat_verileri: Mapping[str, pd.DataFrame],
    ) -> float:
        getiriler = []
        for veri in fiyat_verileri.values():
            if len(veri) < 2:
                continue
            ilk = float(veri["Close"].iloc[0])
            son = float(veri["Close"].iloc[-1])
            getiriler.append(son / ilk - 1.0)

        if not getiriler:
            raise PortfolioCapacityRobustnessError(
                "Pencere piyasa getirisi hesaplanamadı."
            )
        return sum(getiriler) / len(getiriler)

    @staticmethod
    def _piyasa_grubunu_belirle(
        getiri_orani: float,
        medyan_getiri_orani: float | None,
    ) -> str:
        if medyan_getiri_orani is None:
            return PIYASA_NOTR
        if isclose(getiri_orani, medyan_getiri_orani, abs_tol=1e-12):
            return PIYASA_NOTR
        return PIYASA_GUCLU if getiri_orani > medyan_getiri_orani else PIYASA_ZAYIF

    @staticmethod
    def _senaryoyu_bul(
        rapor: PortfolioCapacitySensitivityReport,
        kapasite: int,
    ) -> PortfolioCapacityScenario:
        return next(
            senaryo
            for senaryo in rapor.senaryolar
            if senaryo.kapasite == kapasite
        )

    def _kapasite_ozetlerini_olustur(
        self,
        pencereler: tuple[RollingCapacityWindow, ...],
        kapasiteler: Sequence[int],
    ) -> tuple[CapacityWindowSummary, ...]:
        ozetler = []
        for kapasite in sorted(tuple(kapasiteler)):
            senaryolar = tuple(
                self._senaryoyu_bul(pencere.kapasite_raporu, kapasite)
                for pencere in pencereler
            )
            oranlar = tuple(
                senaryo.getiri_dusus_orani
                for senaryo in senaryolar
                if senaryo.getiri_dusus_orani is not None
            )
            ozetler.append(
                CapacityWindowSummary(
                    kapasite=kapasite,
                    pencere_sayisi=len(senaryolar),
                    pozitif_pencere_sayisi=sum(
                        senaryo.rapor.toplam_getiri_orani > 0
                        for senaryo in senaryolar
                    ),
                    getiri_liderligi_sayisi=sum(
                        pencere.getiri_lideri == kapasite
                        for pencere in pencereler
                    ),
                    getiri_dusus_liderligi_sayisi=sum(
                        pencere.getiri_dusus_lideri == kapasite
                        for pencere in pencereler
                    ),
                    medyan_getiri_orani=(
                        median(
                            senaryo.rapor.toplam_getiri_orani
                            for senaryo in senaryolar
                        )
                        if senaryolar
                        else 0.0
                    ),
                    medyan_maksimum_dusus_orani=(
                        median(
                            senaryo.rapor.maksimum_dusus_orani
                            for senaryo in senaryolar
                        )
                        if senaryolar
                        else 0.0
                    ),
                    medyan_getiri_dusus_orani=(
                        median(oranlar) if oranlar else None
                    ),
                )
            )
        return tuple(ozetler)

    def _sembol_dislamalarini_olustur(
        self,
        fiyat_verileri: Mapping[str, pd.DataFrame],
        islemler: tuple[BacktestTrade, ...],
        kapasiteler: Sequence[int],
        baslangic_sermayesi: float,
        islem_maliyeti_orani: float,
    ) -> tuple[LeaveOneOutScenario, ...]:
        semboller = tuple(sorted(fiyat_verileri))
        dislamalar: tuple[str | None, ...] = (None,) + (
            semboller if len(semboller) > 1 else ()
        )
        senaryolar = []

        for dislanan in dislamalar:
            dahil_semboller = tuple(
                sembol for sembol in semboller if sembol != dislanan
            )
            dahil_veriler = {
                sembol: fiyat_verileri[sembol]
                for sembol in dahil_semboller
            }
            dahil_islemler = tuple(
                islem
                for islem in islemler
                if islem.sembol in dahil_veriler
            )
            kapasite_raporu = self._kapasite_analizcisi.analiz_et(
                fiyat_verileri=dahil_veriler,
                islemler=dahil_islemler,
                kapasiteler=kapasiteler,
                baslangic_sermayesi=baslangic_sermayesi,
                islem_maliyeti_orani=islem_maliyeti_orani,
            )
            senaryolar.append(
                LeaveOneOutScenario(
                    dislanan_sembol=dislanan,
                    dahil_semboller=dahil_semboller,
                    aday_islem_sayisi=len(dahil_islemler),
                    kapasite_raporu=kapasite_raporu,
                )
            )

        return tuple(senaryolar)
