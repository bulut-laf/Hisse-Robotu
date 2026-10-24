from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isclose, isfinite
from statistics import mean
from typing import Iterable, Mapping

import pandas as pd

from .backtest_models import BacktestTrade


PORTFOY_KAPASITE_NEDENI = "Eş zamanlı pozisyon sınırı dolu."
PORTFOY_NAKIT_NEDENI = "Yeterli kullanılabilir nakit yok."
PORTFOY_SEMBOL_CAKISMA_NEDENI = "Aynı sembolde açık pozisyon var."
PORTFOY_RISK_LIMITI_NEDENI = "Toplam açık portföy riski sınırı dolu."

BOYUTLANDIRMA_SABIT = "sabit"
BOYUTLANDIRMA_RISK = "risk"
GECERLI_BOYUTLANDIRMA_MODLARI = (
    BOYUTLANDIRMA_SABIT,
    BOYUTLANDIRMA_RISK,
)


class PortfolioBacktestError(ValueError):
    """Portföy backtest girdileri veya hesaplaması geçersizdir."""


@dataclass(frozen=True)
class PortfolioBacktestConfig:
    """Çoklu hisse portföyü için sermaye, kapasite ve risk ayarları."""

    baslangic_sermayesi: float = 100_000.0
    maksimum_es_zamanli_pozisyon: int = 3
    pozisyon_basina_sermaye_orani: float | None = None
    islem_maliyeti_orani: float = 0.001
    boyutlandirma_modu: str = BOYUTLANDIRMA_SABIT
    zarar_durdur_orani: float | None = None
    islem_basina_risk_orani: float | None = None
    toplam_acik_risk_orani: float | None = None

    def __post_init__(self) -> None:
        if (
            not isfinite(self.baslangic_sermayesi)
            or self.baslangic_sermayesi <= 0
        ):
            raise ValueError(
                "Başlangıç sermayesi pozitif ve sonlu olmalıdır."
            )

        if self.maksimum_es_zamanli_pozisyon <= 0:
            raise ValueError(
                "Maksimum eş zamanlı pozisyon sayısı pozitif olmalıdır."
            )

        temiz_mod = self.boyutlandirma_modu.strip().casefold()
        if temiz_mod not in GECERLI_BOYUTLANDIRMA_MODLARI:
            raise ValueError(
                "Pozisyon boyutlandırma modu sabit veya risk olmalıdır."
            )
        object.__setattr__(self, "boyutlandirma_modu", temiz_mod)

        oran = self.pozisyon_basina_sermaye_orani
        if oran is None:
            oran = 1.0 / self.maksimum_es_zamanli_pozisyon
            object.__setattr__(
                self,
                "pozisyon_basina_sermaye_orani",
                oran,
            )

        if not isfinite(oran) or oran <= 0 or oran > 1:
            raise ValueError(
                "Pozisyon başına sermaye oranı 0 ile 1 arasında olmalıdır."
            )

        if (
            not isfinite(self.islem_maliyeti_orani)
            or self.islem_maliyeti_orani < 0
            or self.islem_maliyeti_orani >= 0.10
        ):
            raise ValueError(
                "İşlem maliyeti oranı 0 ile 0.10 arasında olmalıdır."
            )

        self._opsiyonel_orani_dogrula(
            "Zarar durdur oranı",
            self.zarar_durdur_orani,
            ust_sinir=1.0,
        )
        self._opsiyonel_orani_dogrula(
            "İşlem başına risk oranı",
            self.islem_basina_risk_orani,
            ust_sinir=0.10,
        )
        self._opsiyonel_orani_dogrula(
            "Toplam açık risk oranı",
            self.toplam_acik_risk_orani,
            ust_sinir=0.50,
        )

        if temiz_mod == BOYUTLANDIRMA_RISK:
            if self.zarar_durdur_orani is None:
                raise ValueError(
                    "Risk bazlı boyutlandırmada zarar durdur oranı gereklidir."
                )
            if self.islem_basina_risk_orani is None:
                raise ValueError(
                    "Risk bazlı boyutlandırmada işlem başına risk oranı gereklidir."
                )
            if self.toplam_acik_risk_orani is None:
                raise ValueError(
                    "Risk bazlı boyutlandırmada toplam açık risk oranı gereklidir."
                )
            if self.toplam_acik_risk_orani < self.islem_basina_risk_orani:
                raise ValueError(
                    "Toplam açık risk oranı işlem başına risk oranından küçük olamaz."
                )

    @staticmethod
    def _opsiyonel_orani_dogrula(
        alan_adi: str,
        deger: float | None,
        ust_sinir: float,
    ) -> None:
        if deger is None:
            return
        if not isfinite(deger) or deger <= 0 or deger >= ust_sinir:
            raise ValueError(
                f"{alan_adi} 0 ile {ust_sinir:.2f} arasında olmalıdır."
            )


@dataclass(frozen=True)
class PortfolioSkippedTrade:
    """Portföy kapasitesi veya sermayesi nedeniyle alınmayan işlem."""

    islem: BacktestTrade
    neden: str


@dataclass(frozen=True)
class PortfolioCompletedTrade:
    """Portföy içinde gerçekleşen işlem, sermaye ve planlanan risk."""

    islem: BacktestTrade
    ayrilan_sermaye: float
    adet: float
    satis_tutari: float
    net_kar: float
    planlanan_risk_tutari: float

    @property
    def gerceklesen_getiri_orani(self) -> float:
        if self.ayrilan_sermaye == 0:
            return 0.0

        return self.net_kar / self.ayrilan_sermaye


@dataclass(frozen=True)
class PortfolioDailyPoint:
    """Bir işlem günü sonundaki portföy özsermayesi ve açık riski."""

    tarih: date
    nakit: float
    pozisyon_degeri: float
    ozsermaye: float
    zirve_ozsermaye: float
    dusus_orani: float
    acik_pozisyon_sayisi: int
    sermaye_kullanim_orani: float
    acik_risk_tutari: float
    acik_risk_orani: float


@dataclass(frozen=True)
class PortfolioSymbolContribution:
    """Bir hissenin portföy sonucuna yaptığı gerçekleşmiş katkı."""

    sembol: str
    islem_sayisi: int
    kazanan_islem_sayisi: int
    kaybeden_islem_sayisi: int
    toplam_ayrilan_sermaye: float
    net_kar: float
    baslangic_sermayesine_katki_orani: float

    @property
    def kazanma_orani(self) -> float:
        if self.islem_sayisi == 0:
            return 0.0

        return self.kazanan_islem_sayisi / self.islem_sayisi


@dataclass(frozen=True)
class PortfolioBacktestReport:
    """Çoklu hisse portföyünün işlem, sermaye ve risk raporu."""

    baslangic_sermayesi: float
    bitis_sermayesi: float
    toplam_getiri_orani: float
    maksimum_dusus_orani: float
    guncel_dusus_orani: float
    ortalama_sermaye_kullanim_orani: float
    maksimum_sermaye_kullanim_orani: float
    maksimum_es_zamanli_pozisyon: int
    ortalama_acik_risk_orani: float
    maksimum_acik_risk_orani: float
    maksimum_giris_risk_limiti_kullanim_orani: float
    kar_faktoru: float | None
    kabul_edilen_islemler: tuple[PortfolioCompletedTrade, ...]
    atlanan_islemler: tuple[PortfolioSkippedTrade, ...]
    gunluk_noktalar: tuple[PortfolioDailyPoint, ...]
    sembol_katkilari: tuple[PortfolioSymbolContribution, ...]

    @property
    def tamamlanan_islem_sayisi(self) -> int:
        return len(self.kabul_edilen_islemler)

    @property
    def atlanan_islem_sayisi(self) -> int:
        return len(self.atlanan_islemler)

    @property
    def ilk_tarih(self) -> date | None:
        if not self.gunluk_noktalar:
            return None

        return self.gunluk_noktalar[0].tarih

    @property
    def son_tarih(self) -> date | None:
        if not self.gunluk_noktalar:
            return None

        return self.gunluk_noktalar[-1].tarih


@dataclass
class _OpenPortfolioPosition:
    islem: BacktestTrade
    ayrilan_sermaye: float
    adet: float
    son_fiyat: float
    planlanan_risk_tutari: float


class PortfolioBacktestAnalyzer:
    """
    Önceden üretilmiş çoklu hisse işlemlerini tek ve sınırlı sermaye
    altında kronolojik olarak simüle eder.

    Aynı gün başlayan adaylar skor azalan, sembol artan sırada ele
    alınır. Çıkış günündeki sermaye aynı günün yeni girişlerinde tekrar
    kullanılmaz; bu muhafazakâr yaklaşım gün içi işlem sırası varsayımı
    yapmaz.
    """

    def analiz_et(
        self,
        fiyat_verileri: Mapping[str, pd.DataFrame],
        islemler: Iterable[BacktestTrade],
        yapilandirma: PortfolioBacktestConfig | None = None,
    ) -> PortfolioBacktestReport:
        ayarlar = (
            yapilandirma
            if yapilandirma is not None
            else PortfolioBacktestConfig()
        )

        hazir_veriler = self._fiyat_verilerini_hazirla(fiyat_verileri)
        adaylar = tuple(
            sorted(
                tuple(islemler),
                key=lambda islem: (
                    islem.giris_tarihi,
                    -islem.skor,
                    islem.sembol,
                    islem.sinyal_tarihi,
                    islem.cikis_tarihi,
                ),
            )
        )

        if not adaylar:
            return self._bos_rapor(ayarlar)

        self._islemleri_dogrula(
            islemler=adaylar,
            fiyat_verileri=hazir_veriler,
        )

        ilk_tarih = min(islem.giris_tarihi for islem in adaylar)
        son_tarih = max(islem.cikis_tarihi for islem in adaylar)
        tarihler = self._portfoy_tarihlerini_olustur(
            fiyat_verileri=hazir_veriler,
            ilk_tarih=ilk_tarih,
            son_tarih=son_tarih,
        )

        giris_gruplari: dict[date, list[BacktestTrade]] = {}
        for islem in adaylar:
            giris_gruplari.setdefault(
                islem.giris_tarihi,
                [],
            ).append(islem)

        nakit = ayarlar.baslangic_sermayesi
        zirve = ayarlar.baslangic_sermayesi
        acik_pozisyonlar: list[_OpenPortfolioPosition] = []
        tamamlananlar: list[PortfolioCompletedTrade] = []
        atlananlar: list[PortfolioSkippedTrade] = []
        gunluk_noktalar: list[PortfolioDailyPoint] = []
        maksimum_es_zamanli = 0
        maksimum_giris_risk_limiti_kullanim_orani = 0.0

        for tarih in tarihler:
            self._acik_pozisyon_fiyatlarini_guncelle(
                tarih=tarih,
                acik_pozisyonlar=acik_pozisyonlar,
                fiyat_verileri=hazir_veriler,
                sutun="Open",
            )

            aday_girisler = sorted(
                giris_gruplari.get(tarih, []),
                key=lambda islem: (
                    -islem.skor,
                    islem.sembol,
                    islem.sinyal_tarihi,
                ),
            )

            for islem in aday_girisler:
                if any(
                    pozisyon.islem.sembol == islem.sembol
                    for pozisyon in acik_pozisyonlar
                ):
                    atlananlar.append(
                        PortfolioSkippedTrade(
                            islem=islem,
                            neden=PORTFOY_SEMBOL_CAKISMA_NEDENI,
                        )
                    )
                    continue

                if (
                    len(acik_pozisyonlar)
                    >= ayarlar.maksimum_es_zamanli_pozisyon
                ):
                    atlananlar.append(
                        PortfolioSkippedTrade(
                            islem=islem,
                            neden=PORTFOY_KAPASITE_NEDENI,
                        )
                    )
                    continue

                acilis_ozsermayesi = self._tasfiye_ozsermayesini_hesapla(
                    nakit=nakit,
                    acik_pozisyonlar=acik_pozisyonlar,
                    islem_maliyeti_orani=(
                        ayarlar.islem_maliyeti_orani
                    ),
                )
                hedef_sermaye, planlanan_risk = self._pozisyon_boyutunu_hesapla(
                    acilis_ozsermayesi=acilis_ozsermayesi,
                    ayarlar=ayarlar,
                )

                acik_risk = 0.0
                risk_limiti = 0.0
                if ayarlar.boyutlandirma_modu == BOYUTLANDIRMA_RISK:
                    acik_risk = sum(
                        pozisyon.planlanan_risk_tutari
                        for pozisyon in acik_pozisyonlar
                    )
                    risk_limiti = (
                        acilis_ozsermayesi
                        * float(ayarlar.toplam_acik_risk_orani)
                    )
                    if acik_risk + planlanan_risk > risk_limiti + 1e-9:
                        atlananlar.append(
                            PortfolioSkippedTrade(
                                islem=islem,
                                neden=PORTFOY_RISK_LIMITI_NEDENI,
                            )
                        )
                        continue

                ayrilan_sermaye = min(nakit, hedef_sermaye)

                if ayrilan_sermaye <= 1e-9:
                    atlananlar.append(
                        PortfolioSkippedTrade(
                            islem=islem,
                            neden=PORTFOY_NAKIT_NEDENI,
                        )
                    )
                    continue

                risk_sermaye_orani = self._sermaye_basina_stop_riski(ayarlar)
                planlanan_risk = ayrilan_sermaye * risk_sermaye_orani

                if ayarlar.boyutlandirma_modu == BOYUTLANDIRMA_RISK:
                    giris_risk_limiti_kullanim_orani = (
                        0.0
                        if risk_limiti <= 0
                        else (acik_risk + planlanan_risk) / risk_limiti
                    )
                    maksimum_giris_risk_limiti_kullanim_orani = max(
                        maksimum_giris_risk_limiti_kullanim_orani,
                        giris_risk_limiti_kullanim_orani,
                    )

                maliyetli_giris = (
                    islem.giris_fiyati
                    * (1.0 + ayarlar.islem_maliyeti_orani)
                )
                adet = ayrilan_sermaye / maliyetli_giris
                nakit -= ayrilan_sermaye

                acik_pozisyonlar.append(
                    _OpenPortfolioPosition(
                        islem=islem,
                        ayrilan_sermaye=ayrilan_sermaye,
                        adet=adet,
                        son_fiyat=islem.giris_fiyati,
                        planlanan_risk_tutari=planlanan_risk,
                    )
                )
                maksimum_es_zamanli = max(
                    maksimum_es_zamanli,
                    len(acik_pozisyonlar),
                )

            kalan_pozisyonlar: list[_OpenPortfolioPosition] = []

            for pozisyon in acik_pozisyonlar:
                if tarih == pozisyon.islem.cikis_tarihi:
                    satis_tutari = (
                        pozisyon.adet
                        * pozisyon.islem.cikis_fiyati
                        * (1.0 - ayarlar.islem_maliyeti_orani)
                    )
                    nakit += satis_tutari
                    tamamlananlar.append(
                        PortfolioCompletedTrade(
                            islem=pozisyon.islem,
                            ayrilan_sermaye=pozisyon.ayrilan_sermaye,
                            adet=pozisyon.adet,
                            satis_tutari=satis_tutari,
                            net_kar=(
                                satis_tutari
                                - pozisyon.ayrilan_sermaye
                            ),
                            planlanan_risk_tutari=(
                                pozisyon.planlanan_risk_tutari
                            ),
                        )
                    )
                else:
                    kalan_pozisyonlar.append(pozisyon)

            acik_pozisyonlar = kalan_pozisyonlar

            self._acik_pozisyon_fiyatlarini_guncelle(
                tarih=tarih,
                acik_pozisyonlar=acik_pozisyonlar,
                fiyat_verileri=hazir_veriler,
                sutun="Close",
            )

            pozisyon_degeri = sum(
                pozisyon.adet
                * pozisyon.son_fiyat
                * (1.0 - ayarlar.islem_maliyeti_orani)
                for pozisyon in acik_pozisyonlar
            )
            ozsermaye = nakit + pozisyon_degeri
            zirve = max(zirve, ozsermaye)
            dusus_orani = (
                0.0
                if zirve <= 0
                else 1.0 - ozsermaye / zirve
            )
            kullanim_orani = (
                0.0
                if ozsermaye <= 0
                else pozisyon_degeri / ozsermaye
            )
            acik_risk_tutari = sum(
                pozisyon.planlanan_risk_tutari
                for pozisyon in acik_pozisyonlar
            )
            acik_risk_orani = (
                0.0
                if ozsermaye <= 0
                else acik_risk_tutari / ozsermaye
            )

            gunluk_noktalar.append(
                PortfolioDailyPoint(
                    tarih=tarih,
                    nakit=nakit,
                    pozisyon_degeri=pozisyon_degeri,
                    ozsermaye=ozsermaye,
                    zirve_ozsermaye=zirve,
                    dusus_orani=dusus_orani,
                    acik_pozisyon_sayisi=len(acik_pozisyonlar),
                    sermaye_kullanim_orani=kullanim_orani,
                    acik_risk_tutari=acik_risk_tutari,
                    acik_risk_orani=acik_risk_orani,
                )
            )

        if acik_pozisyonlar:
            raise PortfolioBacktestError(
                "Portföy dönem sonunda açık pozisyon içeriyor."
            )

        bitis_sermayesi = nakit
        toplam_getiri = (
            bitis_sermayesi / ayarlar.baslangic_sermayesi - 1.0
        )
        maksimum_dusus = max(
            (nokta.dusus_orani for nokta in gunluk_noktalar),
            default=0.0,
        )
        guncel_dusus = (
            gunluk_noktalar[-1].dusus_orani
            if gunluk_noktalar
            else 0.0
        )
        kullanimlar = tuple(
            nokta.sermaye_kullanim_orani
            for nokta in gunluk_noktalar
        )
        acik_risk_oranlari = tuple(
            nokta.acik_risk_orani
            for nokta in gunluk_noktalar
        )

        return PortfolioBacktestReport(
            baslangic_sermayesi=ayarlar.baslangic_sermayesi,
            bitis_sermayesi=bitis_sermayesi,
            toplam_getiri_orani=toplam_getiri,
            maksimum_dusus_orani=maksimum_dusus,
            guncel_dusus_orani=guncel_dusus,
            ortalama_sermaye_kullanim_orani=(
                mean(kullanimlar) if kullanimlar else 0.0
            ),
            maksimum_sermaye_kullanim_orani=(
                max(kullanimlar) if kullanimlar else 0.0
            ),
            maksimum_es_zamanli_pozisyon=maksimum_es_zamanli,
            ortalama_acik_risk_orani=(
                mean(acik_risk_oranlari) if acik_risk_oranlari else 0.0
            ),
            maksimum_acik_risk_orani=(
                max(acik_risk_oranlari) if acik_risk_oranlari else 0.0
            ),
            maksimum_giris_risk_limiti_kullanim_orani=(
                maksimum_giris_risk_limiti_kullanim_orani
            ),
            kar_faktoru=self._kar_faktorunu_hesapla(tamamlananlar),
            kabul_edilen_islemler=tuple(tamamlananlar),
            atlanan_islemler=tuple(atlananlar),
            gunluk_noktalar=tuple(gunluk_noktalar),
            sembol_katkilari=self._sembol_katkilarini_hesapla(
                tamamlanan_islemler=tamamlananlar,
                baslangic_sermayesi=ayarlar.baslangic_sermayesi,
            ),
        )

    @staticmethod
    def _bos_rapor(
        ayarlar: PortfolioBacktestConfig,
    ) -> PortfolioBacktestReport:
        return PortfolioBacktestReport(
            baslangic_sermayesi=ayarlar.baslangic_sermayesi,
            bitis_sermayesi=ayarlar.baslangic_sermayesi,
            toplam_getiri_orani=0.0,
            maksimum_dusus_orani=0.0,
            guncel_dusus_orani=0.0,
            ortalama_sermaye_kullanim_orani=0.0,
            maksimum_sermaye_kullanim_orani=0.0,
            maksimum_es_zamanli_pozisyon=0,
            ortalama_acik_risk_orani=0.0,
            maksimum_acik_risk_orani=0.0,
            maksimum_giris_risk_limiti_kullanim_orani=0.0,
            kar_faktoru=None,
            kabul_edilen_islemler=(),
            atlanan_islemler=(),
            gunluk_noktalar=(),
            sembol_katkilari=(),
        )

    @staticmethod
    def _fiyat_verilerini_hazirla(
        fiyat_verileri: Mapping[str, pd.DataFrame],
    ) -> dict[str, pd.DataFrame]:
        if not isinstance(fiyat_verileri, Mapping):
            raise PortfolioBacktestError(
                "Fiyat verileri sembol-DataFrame eşlemesi olmalıdır."
            )

        sonuc: dict[str, pd.DataFrame] = {}

        for ham_sembol, ham_veri in fiyat_verileri.items():
            sembol = str(ham_sembol).strip().upper()

            if not sembol:
                raise PortfolioBacktestError(
                    "Fiyat verisi sembolü boş olamaz."
                )

            if not isinstance(ham_veri, pd.DataFrame):
                raise PortfolioBacktestError(
                    f"{sembol} fiyat verisi pandas DataFrame olmalıdır."
                )

            if ham_veri.empty:
                raise PortfolioBacktestError(
                    f"{sembol} fiyat verisi boş olamaz."
                )

            eksikler = [
                sutun
                for sutun in ("Open", "Close")
                if sutun not in ham_veri.columns
            ]
            if eksikler:
                raise PortfolioBacktestError(
                    f"{sembol} fiyat verisinde eksik sütunlar: "
                    + ", ".join(eksikler)
                )

            veri = ham_veri.copy()
            tarihler = pd.to_datetime(veri.index, errors="coerce")

            if tarihler.isna().any():
                raise PortfolioBacktestError(
                    f"{sembol} fiyat verisinde geçersiz tarihler var."
                )

            if tarihler.tz is not None:
                tarihler = tarihler.tz_localize(None)

            veri.index = tarihler.normalize()
            veri = veri.sort_index()
            veri = veri.loc[~veri.index.duplicated(keep="last")]

            for sutun in ("Open", "Close"):
                veri[sutun] = pd.to_numeric(
                    veri[sutun],
                    errors="coerce",
                )

            if veri[["Open", "Close"]].isna().any().any():
                raise PortfolioBacktestError(
                    f"{sembol} fiyat verisinde eksik veya sayısal olmayan "
                    "Open/Close değeri var."
                )

            if (veri[["Open", "Close"]] <= 0).any().any():
                raise PortfolioBacktestError(
                    f"{sembol} Open/Close değerleri pozitif olmalıdır."
                )

            sonuc[sembol] = veri

        return sonuc

    @staticmethod
    def _islemleri_dogrula(
        islemler: tuple[BacktestTrade, ...],
        fiyat_verileri: Mapping[str, pd.DataFrame],
    ) -> None:
        for islem in islemler:
            veri = fiyat_verileri.get(islem.sembol)

            if veri is None:
                raise PortfolioBacktestError(
                    f"{islem.sembol} işlemi için fiyat verisi bulunamadı."
                )

            mevcut_tarihler = set(veri.index.date)

            if islem.giris_tarihi not in mevcut_tarihler:
                raise PortfolioBacktestError(
                    f"{islem.sembol} giriş tarihi fiyat verisinde yok: "
                    f"{islem.giris_tarihi.isoformat()}"
                )

            if islem.cikis_tarihi not in mevcut_tarihler:
                raise PortfolioBacktestError(
                    f"{islem.sembol} çıkış tarihi fiyat verisinde yok: "
                    f"{islem.cikis_tarihi.isoformat()}"
                )

    @staticmethod
    def _portfoy_tarihlerini_olustur(
        fiyat_verileri: Mapping[str, pd.DataFrame],
        ilk_tarih: date,
        son_tarih: date,
    ) -> tuple[date, ...]:
        tarihler = {
            zaman.date()
            for veri in fiyat_verileri.values()
            for zaman in veri.index
            if ilk_tarih <= zaman.date() <= son_tarih
        }

        if not tarihler:
            raise PortfolioBacktestError(
                "Portföy işlem aralığında fiyat tarihi bulunamadı."
            )

        return tuple(sorted(tarihler))

    @staticmethod
    def _acik_pozisyon_fiyatlarini_guncelle(
        tarih: date,
        acik_pozisyonlar: list[_OpenPortfolioPosition],
        fiyat_verileri: Mapping[str, pd.DataFrame],
        sutun: str,
    ) -> None:
        zaman = pd.Timestamp(tarih)

        for pozisyon in acik_pozisyonlar:
            veri = fiyat_verileri[pozisyon.islem.sembol]

            if zaman in veri.index:
                pozisyon.son_fiyat = float(veri.at[zaman, sutun])

    @classmethod
    def _pozisyon_boyutunu_hesapla(
        cls,
        acilis_ozsermayesi: float,
        ayarlar: PortfolioBacktestConfig,
    ) -> tuple[float, float]:
        sermaye_tavani = (
            acilis_ozsermayesi
            * float(ayarlar.pozisyon_basina_sermaye_orani)
        )
        stop_riski = cls._sermaye_basina_stop_riski(ayarlar)

        if ayarlar.boyutlandirma_modu == BOYUTLANDIRMA_RISK:
            risk_butcesi = (
                acilis_ozsermayesi
                * float(ayarlar.islem_basina_risk_orani)
            )
            hedef_sermaye = min(
                sermaye_tavani,
                risk_butcesi / stop_riski,
            )
        else:
            hedef_sermaye = sermaye_tavani

        return hedef_sermaye, hedef_sermaye * stop_riski

    @staticmethod
    def _sermaye_basina_stop_riski(
        ayarlar: PortfolioBacktestConfig,
    ) -> float:
        if ayarlar.zarar_durdur_orani is None:
            return 0.0

        maliyet = ayarlar.islem_maliyeti_orani
        net_stop_degeri = (
            (1.0 - ayarlar.zarar_durdur_orani)
            * (1.0 - maliyet)
            / (1.0 + maliyet)
        )
        return 1.0 - net_stop_degeri

    @staticmethod
    def _tasfiye_ozsermayesini_hesapla(
        nakit: float,
        acik_pozisyonlar: Iterable[_OpenPortfolioPosition],
        islem_maliyeti_orani: float,
    ) -> float:
        return nakit + sum(
            pozisyon.adet
            * pozisyon.son_fiyat
            * (1.0 - islem_maliyeti_orani)
            for pozisyon in acik_pozisyonlar
        )

    @staticmethod
    def _kar_faktorunu_hesapla(
        islemler: Iterable[PortfolioCompletedTrade],
    ) -> float | None:
        karlar = [islem.net_kar for islem in islemler if islem.net_kar > 0]
        zararlar = [islem.net_kar for islem in islemler if islem.net_kar < 0]

        toplam_zarar = abs(sum(zararlar))

        if isclose(toplam_zarar, 0.0, abs_tol=1e-12):
            return None

        return sum(karlar) / toplam_zarar

    @staticmethod
    def _sembol_katkilarini_hesapla(
        tamamlanan_islemler: Iterable[PortfolioCompletedTrade],
        baslangic_sermayesi: float,
    ) -> tuple[PortfolioSymbolContribution, ...]:
        gruplar: dict[str, list[PortfolioCompletedTrade]] = {}

        for islem in tamamlanan_islemler:
            gruplar.setdefault(islem.islem.sembol, []).append(islem)

        katkilar: list[PortfolioSymbolContribution] = []

        for sembol, sembol_islemleri in gruplar.items():
            net_kar = sum(islem.net_kar for islem in sembol_islemleri)
            kazanan = sum(1 for islem in sembol_islemleri if islem.net_kar > 0)
            kaybeden = sum(1 for islem in sembol_islemleri if islem.net_kar < 0)

            katkilar.append(
                PortfolioSymbolContribution(
                    sembol=sembol,
                    islem_sayisi=len(sembol_islemleri),
                    kazanan_islem_sayisi=kazanan,
                    kaybeden_islem_sayisi=kaybeden,
                    toplam_ayrilan_sermaye=sum(
                        islem.ayrilan_sermaye
                        for islem in sembol_islemleri
                    ),
                    net_kar=net_kar,
                    baslangic_sermayesine_katki_orani=(
                        net_kar / baslangic_sermayesi
                    ),
                )
            )

        return tuple(
            sorted(
                katkilar,
                key=lambda katki: (-katki.net_kar, katki.sembol),
            )
        )
