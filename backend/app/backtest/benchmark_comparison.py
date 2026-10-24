from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite

import pandas as pd


class BenchmarkComparisonError(ValueError):
    """Al-tut ve strateji karşılaştırma hatası."""


@dataclass(frozen=True)
class BuyHoldPerformance:
    """Aynı dönem için al-tut performansı."""

    baslangic_tarihi: date
    bitis_tarihi: date
    giris_fiyati: float
    cikis_fiyati: float
    brut_getiri_orani: float
    net_getiri_orani: float
    yilliklandirilmis_getiri_orani: float
    baslangic_sermayesi: float
    bitis_sermayesi: float
    maksimum_dusus_orani: float
    maksimum_dusus_zirve_tarihi: date
    maksimum_dusus_dip_tarihi: date
    maksimum_dusus_toparlanma_tarihi: date | None
    guncel_dusus_orani: float
    getiri_dusus_orani: float | None
    yillik_getiri_dusus_orani: float | None
    takvim_gunu_sayisi: int

    @property
    def toparlandi_mi(self) -> bool:
        return (
            self.maksimum_dusus_toparlanma_tarihi
            is not None
        )


@dataclass(frozen=True)
class StrategyBenchmarkComparison:
    """Strateji ile al-tut sonuçlarının karşılaştırması."""

    strateji_toplam_getiri_orani: float
    al_tut_toplam_getiri_orani: float
    fazla_getiri_orani: float
    strateji_yilliklandirilmis_getiri_orani: float
    al_tut_yilliklandirilmis_getiri_orani: float
    strateji_maksimum_dusus_orani: float
    al_tut_maksimum_dusus_orani: float
    strateji_getiri_dusus_orani: float | None
    al_tut_getiri_dusus_orani: float | None
    strateji_yillik_getiri_dusus_orani: float | None
    al_tut_yillik_getiri_dusus_orani: float | None
    toplam_getiri_lideri: str
    risk_duzeltilmis_lider: str


@dataclass(frozen=True)
class BenchmarkComparisonReport:
    """Al-tut performansı ve strateji karşılaştırma raporu."""

    al_tut: BuyHoldPerformance
    karsilastirma: StrategyBenchmarkComparison


class BenchmarkComparisonAnalyzer:
    """
    Stratejiyi aynı tarih aralığındaki al-tut
    performansıyla karşılaştırır.

    Al-tut işlemi başlangıç gününün açılış fiyatından
    alınmış ve dönem sonunun kapanış fiyatından satılmış
    kabul edilir.

    Maksimum düşüş, başlangıç tarihinden itibaren günlük
    kapanış fiyatları üzerinden hesaplanır.
    """

    def analiz_et(
        self,
        fiyat_verisi: pd.DataFrame,
        strateji_toplam_getiri_orani: float,
        strateji_maksimum_dusus_orani: float,
        baslangic_tarihi: date | None = None,
        bitis_tarihi: date | None = None,
        baslangic_sermayesi: float = 100_000.0,
        islem_maliyeti_orani: float = 0.001,
    ) -> BenchmarkComparisonReport:
        self._ayarlari_dogrula(
            strateji_toplam_getiri_orani=(
                strateji_toplam_getiri_orani
            ),
            strateji_maksimum_dusus_orani=(
                strateji_maksimum_dusus_orani
            ),
            baslangic_sermayesi=(
                baslangic_sermayesi
            ),
            islem_maliyeti_orani=(
                islem_maliyeti_orani
            ),
        )

        hazir_veri = self._fiyat_verisini_hazirla(
            fiyat_verisi
        )

        if baslangic_tarihi is not None:
            hazir_veri = hazir_veri.loc[
                hazir_veri.index.date
                >= baslangic_tarihi
            ]

        if bitis_tarihi is not None:
            hazir_veri = hazir_veri.loc[
                hazir_veri.index.date
                <= bitis_tarihi
            ]

        if hazir_veri.empty:
            raise BenchmarkComparisonError(
                "Seçilen tarih aralığında fiyat "
                "verisi bulunamadı."
            )

        ilk_satir = hazir_veri.iloc[0]
        son_satir = hazir_veri.iloc[-1]

        gercek_baslangic_tarihi = (
            hazir_veri.index[0]
            .date()
        )

        gercek_bitis_tarihi = (
            hazir_veri.index[-1]
            .date()
        )

        takvim_gunu_sayisi = (
            gercek_bitis_tarihi
            - gercek_baslangic_tarihi
        ).days

        if takvim_gunu_sayisi <= 0:
            raise BenchmarkComparisonError(
                "Karşılaştırma için başlangıç ve bitiş "
                "tarihleri arasında en az bir gün "
                "bulunmalıdır."
            )

        giris_fiyati = float(
            ilk_satir["Open"]
        )

        cikis_fiyati = float(
            son_satir["Close"]
        )

        self._fiyati_dogrula(
            giris_fiyati,
            "Giriş fiyatı",
        )

        self._fiyati_dogrula(
            cikis_fiyati,
            "Çıkış fiyatı",
        )

        brut_getiri_orani = (
            cikis_fiyati
            / giris_fiyati
            - 1.0
        )

        net_getiri_orani = (
            (
                cikis_fiyati
                * (
                    1.0
                    - islem_maliyeti_orani
                )
            )
            / (
                giris_fiyati
                * (
                    1.0
                    + islem_maliyeti_orani
                )
            )
            - 1.0
        )

        adet = (
            baslangic_sermayesi
            / (
                giris_fiyati
                * (
                    1.0
                    + islem_maliyeti_orani
                )
            )
        )

        bitis_sermayesi = (
            adet
            * cikis_fiyati
            * (
                1.0
                - islem_maliyeti_orani
            )
        )

        (
            maksimum_dusus_orani,
            maksimum_dusus_zirve_tarihi,
            maksimum_dusus_dip_tarihi,
            maksimum_dusus_toparlanma_tarihi,
            guncel_dusus_orani,
        ) = self._al_tut_dususunu_hesapla(
            fiyat_verisi=hazir_veri,
            adet=adet,
            baslangic_sermayesi=(
                baslangic_sermayesi
            ),
            islem_maliyeti_orani=(
                islem_maliyeti_orani
            ),
        )

        al_tut_yillik_getiri = (
            self._yilliklandirilmis_getiriyi_hesapla(
                toplam_getiri_orani=(
                    net_getiri_orani
                ),
                takvim_gunu_sayisi=(
                    takvim_gunu_sayisi
                ),
            )
        )

        strateji_yillik_getiri = (
            self._yilliklandirilmis_getiriyi_hesapla(
                toplam_getiri_orani=(
                    strateji_toplam_getiri_orani
                ),
                takvim_gunu_sayisi=(
                    takvim_gunu_sayisi
                ),
            )
        )

        al_tut_getiri_dusus_orani = (
            self._oran_hesapla(
                pay=net_getiri_orani,
                payda=maksimum_dusus_orani,
            )
        )

        strateji_getiri_dusus_orani = (
            self._oran_hesapla(
                pay=(
                    strateji_toplam_getiri_orani
                ),
                payda=(
                    strateji_maksimum_dusus_orani
                ),
            )
        )

        al_tut_yillik_getiri_dusus_orani = (
            self._oran_hesapla(
                pay=al_tut_yillik_getiri,
                payda=maksimum_dusus_orani,
            )
        )

        strateji_yillik_getiri_dusus_orani = (
            self._oran_hesapla(
                pay=strateji_yillik_getiri,
                payda=(
                    strateji_maksimum_dusus_orani
                ),
            )
        )

        al_tut_performansi = BuyHoldPerformance(
            baslangic_tarihi=(
                gercek_baslangic_tarihi
            ),
            bitis_tarihi=(
                gercek_bitis_tarihi
            ),
            giris_fiyati=giris_fiyati,
            cikis_fiyati=cikis_fiyati,
            brut_getiri_orani=(
                brut_getiri_orani
            ),
            net_getiri_orani=(
                net_getiri_orani
            ),
            yilliklandirilmis_getiri_orani=(
                al_tut_yillik_getiri
            ),
            baslangic_sermayesi=(
                baslangic_sermayesi
            ),
            bitis_sermayesi=(
                bitis_sermayesi
            ),
            maksimum_dusus_orani=(
                maksimum_dusus_orani
            ),
            maksimum_dusus_zirve_tarihi=(
                maksimum_dusus_zirve_tarihi
            ),
            maksimum_dusus_dip_tarihi=(
                maksimum_dusus_dip_tarihi
            ),
            maksimum_dusus_toparlanma_tarihi=(
                maksimum_dusus_toparlanma_tarihi
            ),
            guncel_dusus_orani=(
                guncel_dusus_orani
            ),
            getiri_dusus_orani=(
                al_tut_getiri_dusus_orani
            ),
            yillik_getiri_dusus_orani=(
                al_tut_yillik_getiri_dusus_orani
            ),
            takvim_gunu_sayisi=(
                takvim_gunu_sayisi
            ),
        )

        karsilastirma = (
            StrategyBenchmarkComparison(
                strateji_toplam_getiri_orani=(
                    strateji_toplam_getiri_orani
                ),
                al_tut_toplam_getiri_orani=(
                    net_getiri_orani
                ),
                fazla_getiri_orani=(
                    strateji_toplam_getiri_orani
                    - net_getiri_orani
                ),
                strateji_yilliklandirilmis_getiri_orani=(
                    strateji_yillik_getiri
                ),
                al_tut_yilliklandirilmis_getiri_orani=(
                    al_tut_yillik_getiri
                ),
                strateji_maksimum_dusus_orani=(
                    strateji_maksimum_dusus_orani
                ),
                al_tut_maksimum_dusus_orani=(
                    maksimum_dusus_orani
                ),
                strateji_getiri_dusus_orani=(
                    strateji_getiri_dusus_orani
                ),
                al_tut_getiri_dusus_orani=(
                    al_tut_getiri_dusus_orani
                ),
                strateji_yillik_getiri_dusus_orani=(
                    strateji_yillik_getiri_dusus_orani
                ),
                al_tut_yillik_getiri_dusus_orani=(
                    al_tut_yillik_getiri_dusus_orani
                ),
                toplam_getiri_lideri=(
                    self._lideri_bul(
                        strateji_toplam_getiri_orani,
                        net_getiri_orani,
                    )
                ),
                risk_duzeltilmis_lider=(
                    self._opsiyonel_lideri_bul(
                        strateji_yillik_getiri_dusus_orani,
                        al_tut_yillik_getiri_dusus_orani,
                    )
                ),
            )
        )

        return BenchmarkComparisonReport(
            al_tut=al_tut_performansi,
            karsilastirma=karsilastirma,
        )

    @staticmethod
    def _fiyat_verisini_hazirla(
        fiyat_verisi: pd.DataFrame,
    ) -> pd.DataFrame:
        if not isinstance(
            fiyat_verisi,
            pd.DataFrame,
        ):
            raise BenchmarkComparisonError(
                "Fiyat verisi pandas DataFrame "
                "olmalıdır."
            )

        if fiyat_verisi.empty:
            raise BenchmarkComparisonError(
                "Fiyat verisi boş olamaz."
            )

        gerekli_sutunlar = {
            "Open",
            "Close",
        }

        eksik_sutunlar = (
            gerekli_sutunlar
            - set(
                fiyat_verisi.columns
            )
        )

        if eksik_sutunlar:
            raise BenchmarkComparisonError(
                "Eksik fiyat sütunları: "
                + ", ".join(
                    sorted(
                        eksik_sutunlar
                    )
                )
            )

        kopya = fiyat_verisi.copy()

        tarihler = pd.to_datetime(
            kopya.index,
            errors="coerce",
        )

        if tarihler.isna().any():
            raise BenchmarkComparisonError(
                "Fiyat verisinde geçersiz tarihler var."
            )

        kopya.index = tarihler

        kopya = (
            kopya
            .sort_index()
        )

        kopya = kopya.loc[
            ~kopya.index.duplicated(
                keep="last"
            )
        ]

        for sutun in (
            "Open",
            "Close",
        ):
            kopya[sutun] = pd.to_numeric(
                kopya[sutun],
                errors="coerce",
            )

        if (
            kopya[
                [
                    "Open",
                    "Close",
                ]
            ]
            .isna()
            .any()
            .any()
        ):
            raise BenchmarkComparisonError(
                "Fiyat verisinde sayısal olmayan "
                "veya eksik değerler var."
            )

        if (
            (
                kopya["Open"] <= 0
            ).any()
            or (
                kopya["Close"] <= 0
            ).any()
        ):
            raise BenchmarkComparisonError(
                "Fiyat değerleri pozitif olmalıdır."
            )

        return kopya

    @staticmethod
    def _ayarlari_dogrula(
        strateji_toplam_getiri_orani: float,
        strateji_maksimum_dusus_orani: float,
        baslangic_sermayesi: float,
        islem_maliyeti_orani: float,
    ) -> None:
        if not isfinite(
            strateji_toplam_getiri_orani
        ):
            raise BenchmarkComparisonError(
                "Strateji toplam getirisi sonlu "
                "olmalıdır."
            )

        if (
            strateji_toplam_getiri_orani
            <= -1.0
        ):
            raise BenchmarkComparisonError(
                "Strateji toplam getirisi -%100 veya "
                "daha düşük olamaz."
            )

        if (
            not isfinite(
                strateji_maksimum_dusus_orani
            )
            or strateji_maksimum_dusus_orani < 0
            or strateji_maksimum_dusus_orani > 1
        ):
            raise BenchmarkComparisonError(
                "Strateji maksimum düşüşü 0 ile 1 "
                "arasında olmalıdır."
            )

        if (
            not isfinite(
                baslangic_sermayesi
            )
            or baslangic_sermayesi <= 0
        ):
            raise BenchmarkComparisonError(
                "Başlangıç sermayesi pozitif ve "
                "sonlu olmalıdır."
            )

        if (
            not isfinite(
                islem_maliyeti_orani
            )
            or islem_maliyeti_orani < 0
            or islem_maliyeti_orani >= 1
        ):
            raise BenchmarkComparisonError(
                "İşlem maliyeti oranı 0 ile 1 "
                "arasında olmalıdır."
            )

    @staticmethod
    def _fiyati_dogrula(
        fiyat: float,
        alan_adi: str,
    ) -> None:
        if (
            not isfinite(
                fiyat
            )
            or fiyat <= 0
        ):
            raise BenchmarkComparisonError(
                f"{alan_adi} pozitif ve sonlu "
                "olmalıdır."
            )

    @staticmethod
    def _yilliklandirilmis_getiriyi_hesapla(
        toplam_getiri_orani: float,
        takvim_gunu_sayisi: int,
    ) -> float:
        getiri_carpani = (
            1.0
            + toplam_getiri_orani
        )

        if getiri_carpani <= 0:
            raise BenchmarkComparisonError(
                "Toplam getiri yıllıklandırılamıyor."
            )

        return (
            getiri_carpani
            ** (
                365.0
                / takvim_gunu_sayisi
            )
            - 1.0
        )

    @staticmethod
    def _oran_hesapla(
        pay: float,
        payda: float,
    ) -> float | None:
        if payda == 0:
            return None

        return (
            pay
            / payda
        )

    @staticmethod
    def _lideri_bul(
        strateji_degeri: float,
        al_tut_degeri: float,
    ) -> str:
        fark = (
            strateji_degeri
            - al_tut_degeri
        )

        if abs(fark) < 1e-12:
            return "Eşit"

        if fark > 0:
            return "Strateji"

        return "Al-Tut"

    @staticmethod
    def _opsiyonel_lideri_bul(
        strateji_degeri: float | None,
        al_tut_degeri: float | None,
    ) -> str:
        if (
            strateji_degeri is None
            and al_tut_degeri is None
        ):
            return "Hesaplanamadı"

        if strateji_degeri is None:
            return "Al-Tut"

        if al_tut_degeri is None:
            return "Strateji"

        return (
            BenchmarkComparisonAnalyzer
            ._lideri_bul(
                strateji_degeri,
                al_tut_degeri,
            )
        )

    @staticmethod
    def _al_tut_dususunu_hesapla(
        fiyat_verisi: pd.DataFrame,
        adet: float,
        baslangic_sermayesi: float,
        islem_maliyeti_orani: float,
    ) -> tuple[
        float,
        date,
        date,
        date | None,
        float,
    ]:
        zirve_sermayesi = baslangic_sermayesi

        ilk_tarih = (
            fiyat_verisi.index[0]
            .date()
        )

        zirve_tarihi = ilk_tarih
        maksimum_dusus_orani = 0.0
        maksimum_zirve_tarihi = ilk_tarih
        maksimum_dip_tarihi = ilk_tarih
        maksimum_zirve_sermayesi = (
            baslangic_sermayesi
        )

        sermaye_noktalari: list[
            tuple[date, float]
        ] = []

        for zaman, satir in (
            fiyat_verisi.iterrows()
        ):
            tarih = zaman.date()

            sermaye = (
                adet
                * float(
                    satir["Close"]
                )
                * (
                    1.0
                    - islem_maliyeti_orani
                )
            )

            sermaye_noktalari.append(
                (
                    tarih,
                    sermaye,
                )
            )

            if sermaye > zirve_sermayesi:
                zirve_sermayesi = sermaye
                zirve_tarihi = tarih

            dusus_orani = (
                1.0
                - sermaye
                / zirve_sermayesi
            )

            if (
                dusus_orani
                > maksimum_dusus_orani
            ):
                maksimum_dusus_orani = (
                    dusus_orani
                )

                maksimum_zirve_tarihi = (
                    zirve_tarihi
                )

                maksimum_dip_tarihi = tarih

                maksimum_zirve_sermayesi = (
                    zirve_sermayesi
                )

        toparlanma_tarihi: date | None = None

        dip_goruldu = False

        for tarih, sermaye in sermaye_noktalari:
            if tarih == maksimum_dip_tarihi:
                dip_goruldu = True

            if (
                dip_goruldu
                and sermaye
                >= maksimum_zirve_sermayesi
            ):
                toparlanma_tarihi = tarih
                break

        son_sermaye = (
            sermaye_noktalari[-1][1]
        )

        tum_zamanlar_zirvesi = max(
            baslangic_sermayesi,
            max(
                sermaye
                for _, sermaye
                in sermaye_noktalari
            ),
        )

        guncel_dusus_orani = (
            1.0
            - son_sermaye
            / tum_zamanlar_zirvesi
        )

        return (
            maksimum_dusus_orani,
            maksimum_zirve_tarihi,
            maksimum_dip_tarihi,
            toparlanma_tarihi,
            guncel_dusus_orani,
        )