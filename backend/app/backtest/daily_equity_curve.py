from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite
from typing import Iterable

import pandas as pd

from .backtest_models import BacktestTrade
from .equity_curve import DrawdownPeriod


class DailyEquityCurveError(ValueError):
    """Günlük mark-to-market özsermaye hesaplama hatası."""


@dataclass(frozen=True)
class DailyEquityPoint:
    """Bir işlem gününün kapanışındaki tahmini tasfiye özsermayesi."""

    tarih: date
    sermaye: float
    zirve_sermayesi: float
    dusus_orani: float
    pozisyonda_mi: bool
    islem_sirasi: int | None


@dataclass(frozen=True)
class DailyEquityCurveReport:
    """Günlük fiyatlarla mark-to-market özsermaye ve düşüş raporu."""

    baslangic_sermayesi: float
    bitis_sermayesi: float
    toplam_bilesik_getiri_orani: float
    baslangic_tarihi: date | None
    bitis_tarihi: date | None
    noktalar: tuple[DailyEquityPoint, ...]
    dusus_donemleri: tuple[DrawdownPeriod, ...]
    maksimum_dusus_orani: float
    maksimum_dusus_donemi: DrawdownPeriod | None
    en_uzun_dusus_donemi: DrawdownPeriod | None

    @property
    def islem_gunu_sayisi(self) -> int:
        return len(self.noktalar)

    @property
    def dusus_donemi_sayisi(self) -> int:
        return len(self.dusus_donemleri)

    @property
    def guncel_dusus_orani(self) -> float:
        if not self.noktalar:
            return 0.0

        return self.noktalar[-1].dusus_orani


@dataclass
class _OpenDrawdown:
    zirve_tarihi: date
    zirve_sermayesi: float
    dip_tarihi: date
    dip_sermayesi: float


class DailyEquityCurveAnalyzer:
    """
    Kabul edilmiş ve çakışmayan işlemler için günlük mark-to-market
    özsermaye eğrisi üretir.

    Açık pozisyon günlerinde sermaye, günlük kapanış fiyatından o gün
    tasfiye edilmiş gibi hesaplanır. Gerçek çıkış gününde ise backtest
    motorunun belirlediği çıkış fiyatı kullanılır. Böylece raporun son
    sermayesi tamamlanmış işlem özsermayesiyle aynı kalır.
    """

    def analiz_et(
        self,
        fiyat_verisi: pd.DataFrame,
        islemler: Iterable[BacktestTrade],
        baslangic_sermayesi: float = 100_000.0,
        pozisyon_orani: float = 1.0,
        islem_maliyeti_orani: float = 0.001,
    ) -> DailyEquityCurveReport:
        self._ayarlari_dogrula(
            baslangic_sermayesi=baslangic_sermayesi,
            pozisyon_orani=pozisyon_orani,
            islem_maliyeti_orani=islem_maliyeti_orani,
        )

        sirali_islemler = tuple(
            sorted(
                tuple(islemler),
                key=lambda islem: (
                    islem.giris_tarihi,
                    islem.cikis_tarihi,
                    islem.sinyal_tarihi,
                    islem.sembol,
                ),
            )
        )

        if not sirali_islemler:
            return DailyEquityCurveReport(
                baslangic_sermayesi=baslangic_sermayesi,
                bitis_sermayesi=baslangic_sermayesi,
                toplam_bilesik_getiri_orani=0.0,
                baslangic_tarihi=None,
                bitis_tarihi=None,
                noktalar=(),
                dusus_donemleri=(),
                maksimum_dusus_orani=0.0,
                maksimum_dusus_donemi=None,
                en_uzun_dusus_donemi=None,
            )

        self._islemleri_dogrula(sirali_islemler)
        hazir_veri = self._fiyat_verisini_hazirla(fiyat_verisi)

        ilk_giris_tarihi = sirali_islemler[0].giris_tarihi
        son_cikis_tarihi = sirali_islemler[-1].cikis_tarihi

        tarih_araligi = hazir_veri.loc[
            (hazir_veri.index.date >= ilk_giris_tarihi)
            & (hazir_veri.index.date <= son_cikis_tarihi)
        ]

        if tarih_araligi.empty:
            raise DailyEquityCurveError(
                "İşlem tarihleri için fiyat verisi bulunamadı."
            )

        mevcut_tarihler = set(tarih_araligi.index.date)

        for islem in sirali_islemler:
            if islem.giris_tarihi not in mevcut_tarihler:
                raise DailyEquityCurveError(
                    "İşlem giriş tarihi fiyat verisinde bulunamadı: "
                    f"{islem.giris_tarihi.isoformat()}"
                )

            if islem.cikis_tarihi not in mevcut_tarihler:
                raise DailyEquityCurveError(
                    "İşlem çıkış tarihi fiyat verisinde bulunamadı: "
                    f"{islem.cikis_tarihi.isoformat()}"
                )

        noktalar: list[DailyEquityPoint] = []
        gerceklesen_sermaye = baslangic_sermayesi
        islem_indeksi = 0

        acik_islem: BacktestTrade | None = None
        acik_islem_sirasi: int | None = None
        nakit = gerceklesen_sermaye
        adet = 0.0

        for zaman, satir in tarih_araligi.iterrows():
            tarih = zaman.date()

            if (
                acik_islem is None
                and islem_indeksi < len(sirali_islemler)
                and tarih == sirali_islemler[islem_indeksi].giris_tarihi
            ):
                acik_islem = sirali_islemler[islem_indeksi]
                acik_islem_sirasi = islem_indeksi + 1

                ayrilan_sermaye = (
                    gerceklesen_sermaye
                    * pozisyon_orani
                )

                nakit = (
                    gerceklesen_sermaye
                    - ayrilan_sermaye
                )

                maliyetli_giris = (
                    acik_islem.giris_fiyati
                    * (1.0 + islem_maliyeti_orani)
                )

                adet = ayrilan_sermaye / maliyetli_giris

            pozisyonda_mi = acik_islem is not None

            if acik_islem is None:
                sermaye = gerceklesen_sermaye

            else:
                if tarih == acik_islem.cikis_tarihi:
                    degerleme_fiyati = acik_islem.cikis_fiyati
                else:
                    degerleme_fiyati = float(satir["Close"])

                sermaye = (
                    nakit
                    + adet
                    * degerleme_fiyati
                    * (1.0 - islem_maliyeti_orani)
                )

            noktalar.append(
                DailyEquityPoint(
                    tarih=tarih,
                    sermaye=sermaye,
                    zirve_sermayesi=0.0,
                    dusus_orani=0.0,
                    pozisyonda_mi=pozisyonda_mi,
                    islem_sirasi=acik_islem_sirasi,
                )
            )

            if (
                acik_islem is not None
                and tarih == acik_islem.cikis_tarihi
            ):
                gerceklesen_sermaye = sermaye
                acik_islem = None
                acik_islem_sirasi = None
                nakit = gerceklesen_sermaye
                adet = 0.0
                islem_indeksi += 1

        if acik_islem is not None:
            raise DailyEquityCurveError(
                "Son işlem fiyat dönemi içinde kapatılamadı."
            )

        if islem_indeksi != len(sirali_islemler):
            raise DailyEquityCurveError(
                "Tüm işlemler günlük özsermaye eğrisine işlenemedi."
            )

        (
            tamamlanmis_noktalar,
            dusus_donemleri,
        ) = self._dususleri_hesapla(
            noktalar=tuple(noktalar),
            baslangic_sermayesi=baslangic_sermayesi,
        )

        maksimum_dusus_donemi = (
            max(
                dusus_donemleri,
                key=lambda donem: donem.dusus_orani,
            )
            if dusus_donemleri
            else None
        )

        en_uzun_dusus_donemi = (
            max(
                dusus_donemleri,
                key=lambda donem: donem.zirve_altinda_gun_sayisi,
            )
            if dusus_donemleri
            else None
        )

        maksimum_dusus_orani = (
            maksimum_dusus_donemi.dusus_orani
            if maksimum_dusus_donemi is not None
            else 0.0
        )

        bitis_sermayesi = tamamlanmis_noktalar[-1].sermaye
        toplam_bilesik_getiri_orani = (
            bitis_sermayesi / baslangic_sermayesi - 1.0
        )

        return DailyEquityCurveReport(
            baslangic_sermayesi=baslangic_sermayesi,
            bitis_sermayesi=bitis_sermayesi,
            toplam_bilesik_getiri_orani=(
                toplam_bilesik_getiri_orani
            ),
            baslangic_tarihi=ilk_giris_tarihi,
            bitis_tarihi=son_cikis_tarihi,
            noktalar=tamamlanmis_noktalar,
            dusus_donemleri=dusus_donemleri,
            maksimum_dusus_orani=maksimum_dusus_orani,
            maksimum_dusus_donemi=maksimum_dusus_donemi,
            en_uzun_dusus_donemi=en_uzun_dusus_donemi,
        )

    @staticmethod
    def _ayarlari_dogrula(
        baslangic_sermayesi: float,
        pozisyon_orani: float,
        islem_maliyeti_orani: float,
    ) -> None:
        if (
            not isfinite(baslangic_sermayesi)
            or baslangic_sermayesi <= 0
        ):
            raise DailyEquityCurveError(
                "Başlangıç sermayesi pozitif ve sonlu olmalıdır."
            )

        if (
            not isfinite(pozisyon_orani)
            or pozisyon_orani <= 0
            or pozisyon_orani > 1
        ):
            raise DailyEquityCurveError(
                "Pozisyon oranı 0 ile 1 arasında olmalıdır."
            )

        if (
            not isfinite(islem_maliyeti_orani)
            or islem_maliyeti_orani < 0
            or islem_maliyeti_orani >= 0.10
        ):
            raise DailyEquityCurveError(
                "İşlem maliyeti oranı 0 ile 0.10 arasında olmalıdır."
            )

    @staticmethod
    def _fiyat_verisini_hazirla(
        fiyat_verisi: pd.DataFrame,
    ) -> pd.DataFrame:
        if not isinstance(fiyat_verisi, pd.DataFrame):
            raise DailyEquityCurveError(
                "Fiyat verisi pandas DataFrame olmalıdır."
            )

        if fiyat_verisi.empty:
            raise DailyEquityCurveError(
                "Fiyat verisi boş olamaz."
            )

        if "Close" not in fiyat_verisi.columns:
            raise DailyEquityCurveError(
                "Fiyat verisinde Close sütunu bulunmalıdır."
            )

        kopya = fiyat_verisi.copy()
        tarihler = pd.to_datetime(kopya.index, errors="coerce")

        if tarihler.isna().any():
            raise DailyEquityCurveError(
                "Fiyat verisinde geçersiz tarihler var."
            )

        kopya.index = tarihler
        kopya = kopya.sort_index()
        kopya = kopya.loc[
            ~kopya.index.duplicated(keep="last")
        ]
        kopya["Close"] = pd.to_numeric(
            kopya["Close"],
            errors="coerce",
        )

        if kopya["Close"].isna().any():
            raise DailyEquityCurveError(
                "Fiyat verisinde sayısal olmayan veya eksik "
                "Close değerleri var."
            )

        if (kopya["Close"] <= 0).any():
            raise DailyEquityCurveError(
                "Close değerleri pozitif olmalıdır."
            )

        return kopya

    @staticmethod
    def _islemleri_dogrula(
        islemler: tuple[BacktestTrade, ...],
    ) -> None:
        onceki_islem: BacktestTrade | None = None

        for islem in islemler:
            if not isfinite(islem.giris_fiyati):
                raise DailyEquityCurveError(
                    "İşlem giriş fiyatı sonlu olmalıdır."
                )

            if not isfinite(islem.cikis_fiyati):
                raise DailyEquityCurveError(
                    "İşlem çıkış fiyatı sonlu olmalıdır."
                )

            if (
                onceki_islem is not None
                and islem.giris_tarihi
                <= onceki_islem.cikis_tarihi
            ):
                raise DailyEquityCurveError(
                    "Günlük özsermaye analizi çakışmayan "
                    "işlemler gerektirir."
                )

            onceki_islem = islem

    @staticmethod
    def _dususleri_hesapla(
        noktalar: tuple[DailyEquityPoint, ...],
        baslangic_sermayesi: float,
    ) -> tuple[
        tuple[DailyEquityPoint, ...],
        tuple[DrawdownPeriod, ...],
    ]:
        if not noktalar:
            return (), ()

        zirve_sermayesi = baslangic_sermayesi
        zirve_tarihi = noktalar[0].tarih
        acik_dusus: _OpenDrawdown | None = None
        tamamlanmis_noktalar: list[DailyEquityPoint] = []
        dusus_donemleri: list[DrawdownPeriod] = []

        for nokta in noktalar:
            sermaye = nokta.sermaye

            if sermaye >= zirve_sermayesi:
                if acik_dusus is not None:
                    dusus_donemleri.append(
                        DrawdownPeriod(
                            zirve_tarihi=acik_dusus.zirve_tarihi,
                            dip_tarihi=acik_dusus.dip_tarihi,
                            toparlanma_tarihi=nokta.tarih,
                            zirve_sermayesi=(
                                acik_dusus.zirve_sermayesi
                            ),
                            dip_sermayesi=acik_dusus.dip_sermayesi,
                            dusus_orani=(
                                1.0
                                - acik_dusus.dip_sermayesi
                                / acik_dusus.zirve_sermayesi
                            ),
                            zirve_altinda_gun_sayisi=(
                                nokta.tarih
                                - acik_dusus.zirve_tarihi
                            ).days,
                        )
                    )
                    acik_dusus = None

                zirve_sermayesi = sermaye
                zirve_tarihi = nokta.tarih
                dusus_orani = 0.0

            else:
                dusus_orani = 1.0 - sermaye / zirve_sermayesi

                if acik_dusus is None:
                    acik_dusus = _OpenDrawdown(
                        zirve_tarihi=zirve_tarihi,
                        zirve_sermayesi=zirve_sermayesi,
                        dip_tarihi=nokta.tarih,
                        dip_sermayesi=sermaye,
                    )

                elif sermaye < acik_dusus.dip_sermayesi:
                    acik_dusus.dip_tarihi = nokta.tarih
                    acik_dusus.dip_sermayesi = sermaye

            tamamlanmis_noktalar.append(
                DailyEquityPoint(
                    tarih=nokta.tarih,
                    sermaye=sermaye,
                    zirve_sermayesi=zirve_sermayesi,
                    dusus_orani=dusus_orani,
                    pozisyonda_mi=nokta.pozisyonda_mi,
                    islem_sirasi=nokta.islem_sirasi,
                )
            )

        if acik_dusus is not None:
            son_tarih = noktalar[-1].tarih

            dusus_donemleri.append(
                DrawdownPeriod(
                    zirve_tarihi=acik_dusus.zirve_tarihi,
                    dip_tarihi=acik_dusus.dip_tarihi,
                    toparlanma_tarihi=None,
                    zirve_sermayesi=acik_dusus.zirve_sermayesi,
                    dip_sermayesi=acik_dusus.dip_sermayesi,
                    dusus_orani=(
                        1.0
                        - acik_dusus.dip_sermayesi
                        / acik_dusus.zirve_sermayesi
                    ),
                    zirve_altinda_gun_sayisi=(
                        son_tarih - acik_dusus.zirve_tarihi
                    ).days,
                )
            )

        return (
            tuple(tamamlanmis_noktalar),
            tuple(dusus_donemleri),
        )
