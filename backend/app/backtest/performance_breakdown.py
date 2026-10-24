from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import isfinite
from typing import Iterable

from .backtest_models import BacktestTrade


class PerformanceBreakdownError(ValueError):
    """Performans dağılımı hesaplama hatası."""


@dataclass(frozen=True)
class YearlyPerformance:
    """Bir takvim yılında kapanan işlemlerin performansı."""

    yil: int
    islem_sayisi: int
    kazanan_islem_sayisi: int
    kaybeden_islem_sayisi: int
    basabas_islem_sayisi: int
    kazanma_orani: float
    ortalama_net_getiri_orani: float
    bilesik_getiri_orani: float
    kar_faktoru: float | None
    yil_basi_sermayesi: float
    yil_sonu_sermayesi: float


@dataclass(frozen=True)
class ExitReasonPerformance:
    """Belirli bir çıkış nedenine ait işlem dağılımı."""

    cikis_nedeni: str
    islem_sayisi: int
    toplam_islem_orani: float
    kazanan_islem_sayisi: int
    kaybeden_islem_sayisi: int
    basabas_islem_sayisi: int
    kazanma_orani: float
    ortalama_net_getiri_orani: float
    bilesik_getiri_orani: float


@dataclass(frozen=True)
class PerformanceBreakdownReport:
    """Yıllık ve çıkış nedeni bazlı performans raporu."""

    baslangic_sermayesi: float
    bitis_sermayesi: float
    toplam_bilesik_getiri_orani: float
    yillik_performanslar: tuple[
        YearlyPerformance,
        ...,
    ]
    cikis_nedeni_performanslari: tuple[
        ExitReasonPerformance,
        ...,
    ]
    en_karli_yil: YearlyPerformance | None
    en_zararli_yil: YearlyPerformance | None

    @property
    def yil_sayisi(self) -> int:
        return len(
            self.yillik_performanslar
        )


class PerformanceBreakdownAnalyzer:
    """
    Tamamlanmış backtest işlemlerini yıllara ve
    çıkış nedenlerine göre analiz eder.

    Yıllık sınıflandırmada işlemin çıkış tarihi
    esas alınır. Çünkü getiri o tarihte gerçekleşmiş
    kabul edilir.
    """

    def analiz_et(
        self,
        islemler: Iterable[BacktestTrade],
        baslangic_sermayesi: float = 100_000.0,
        pozisyon_orani: float = 1.0,
    ) -> PerformanceBreakdownReport:
        self._ayarlari_dogrula(
            baslangic_sermayesi=baslangic_sermayesi,
            pozisyon_orani=pozisyon_orani,
        )

        sirali_islemler = tuple(
            sorted(
                tuple(islemler),
                key=lambda islem: (
                    islem.cikis_tarihi,
                    islem.giris_tarihi,
                    islem.sinyal_tarihi,
                    islem.sembol,
                ),
            )
        )

        if not sirali_islemler:
            return PerformanceBreakdownReport(
                baslangic_sermayesi=(
                    baslangic_sermayesi
                ),
                bitis_sermayesi=(
                    baslangic_sermayesi
                ),
                toplam_bilesik_getiri_orani=0.0,
                yillik_performanslar=(),
                cikis_nedeni_performanslari=(),
                en_karli_yil=None,
                en_zararli_yil=None,
            )

        self._islemleri_dogrula(
            sirali_islemler
        )

        yillara_gore: dict[
            int,
            list[BacktestTrade],
        ] = defaultdict(list)

        cikis_nedenlerine_gore: dict[
            str,
            list[BacktestTrade],
        ] = defaultdict(list)

        for islem in sirali_islemler:
            yillara_gore[
                islem.cikis_tarihi.year
            ].append(
                islem
            )

            cikis_nedeni = (
                islem.cikis_nedeni.strip()
                or "Belirtilmedi"
            )

            cikis_nedenlerine_gore[
                cikis_nedeni
            ].append(
                islem
            )

        yillik_performanslar: list[
            YearlyPerformance
        ] = []

        sermaye = baslangic_sermayesi

        for yil in sorted(
            yillara_gore
        ):
            yil_islemleri = tuple(
                yillara_gore[yil]
            )

            yil_basi_sermayesi = sermaye

            for islem in yil_islemleri:
                sermaye = (
                    self._sermayeyi_guncelle(
                        sermaye=sermaye,
                        net_getiri_orani=(
                            islem.net_getiri_orani
                        ),
                        pozisyon_orani=(
                            pozisyon_orani
                        ),
                    )
                )

            yil_sonu_sermayesi = sermaye

            yillik_performanslar.append(
                self._yillik_performans_olustur(
                    yil=yil,
                    islemler=yil_islemleri,
                    yil_basi_sermayesi=(
                        yil_basi_sermayesi
                    ),
                    yil_sonu_sermayesi=(
                        yil_sonu_sermayesi
                    ),
                )
            )

        cikis_nedeni_performanslari = tuple(
            sorted(
                (
                    self._cikis_nedeni_performansi_olustur(
                        cikis_nedeni=cikis_nedeni,
                        islemler=tuple(
                            neden_islemleri
                        ),
                        toplam_islem_sayisi=len(
                            sirali_islemler
                        ),
                        pozisyon_orani=(
                            pozisyon_orani
                        ),
                    )
                    for (
                        cikis_nedeni,
                        neden_islemleri,
                    ) in cikis_nedenlerine_gore.items()
                ),
                key=lambda performans: (
                    -performans.islem_sayisi,
                    performans.cikis_nedeni,
                ),
            )
        )

        yillik_performans_tuple = tuple(
            yillik_performanslar
        )

        en_karli_yil = max(
            yillik_performans_tuple,
            key=lambda performans: (
                performans.bilesik_getiri_orani
            ),
        )

        en_zararli_yil = min(
            yillik_performans_tuple,
            key=lambda performans: (
                performans.bilesik_getiri_orani
            ),
        )

        toplam_bilesik_getiri_orani = (
            sermaye
            / baslangic_sermayesi
            - 1.0
        )

        return PerformanceBreakdownReport(
            baslangic_sermayesi=(
                baslangic_sermayesi
            ),
            bitis_sermayesi=sermaye,
            toplam_bilesik_getiri_orani=(
                toplam_bilesik_getiri_orani
            ),
            yillik_performanslar=(
                yillik_performans_tuple
            ),
            cikis_nedeni_performanslari=(
                cikis_nedeni_performanslari
            ),
            en_karli_yil=en_karli_yil,
            en_zararli_yil=en_zararli_yil,
        )

    @staticmethod
    def _ayarlari_dogrula(
        baslangic_sermayesi: float,
        pozisyon_orani: float,
    ) -> None:
        if (
            not isfinite(
                baslangic_sermayesi
            )
            or baslangic_sermayesi <= 0
        ):
            raise PerformanceBreakdownError(
                "Başlangıç sermayesi pozitif ve "
                "sonlu olmalıdır."
            )

        if (
            not isfinite(
                pozisyon_orani
            )
            or pozisyon_orani <= 0
            or pozisyon_orani > 1
        ):
            raise PerformanceBreakdownError(
                "Pozisyon oranı 0 ile 1 arasında "
                "olmalıdır."
            )

    @staticmethod
    def _islemleri_dogrula(
        islemler: tuple[
            BacktestTrade,
            ...,
        ],
    ) -> None:
        for islem in islemler:
            if not isfinite(
                islem.net_getiri_orani
            ):
                raise PerformanceBreakdownError(
                    "İşlem net getirisi sonlu "
                    "olmalıdır."
                )

    @staticmethod
    def _sermayeyi_guncelle(
        sermaye: float,
        net_getiri_orani: float,
        pozisyon_orani: float,
    ) -> float:
        getiri_carpani = (
            1.0
            + net_getiri_orani
            * pozisyon_orani
        )

        if getiri_carpani <= 0:
            raise PerformanceBreakdownError(
                "İşlem getirisi sermayeyi sıfır "
                "veya negatif değere düşürüyor."
            )

        return (
            sermaye
            * getiri_carpani
        )

    def _yillik_performans_olustur(
        self,
        yil: int,
        islemler: tuple[
            BacktestTrade,
            ...,
        ],
        yil_basi_sermayesi: float,
        yil_sonu_sermayesi: float,
    ) -> YearlyPerformance:
        net_getiriler = tuple(
            islem.net_getiri_orani
            for islem in islemler
        )

        (
            kazanan_sayisi,
            kaybeden_sayisi,
            basabas_sayisi,
        ) = self._sonuc_sayilarini_hesapla(
            net_getiriler
        )

        islem_sayisi = len(
            net_getiriler
        )

        kazanma_orani = (
            kazanan_sayisi
            / islem_sayisi
        )

        ortalama_net_getiri_orani = (
            sum(
                net_getiriler
            )
            / islem_sayisi
        )

        bilesik_getiri_orani = (
            yil_sonu_sermayesi
            / yil_basi_sermayesi
            - 1.0
        )

        return YearlyPerformance(
            yil=yil,
            islem_sayisi=islem_sayisi,
            kazanan_islem_sayisi=(
                kazanan_sayisi
            ),
            kaybeden_islem_sayisi=(
                kaybeden_sayisi
            ),
            basabas_islem_sayisi=(
                basabas_sayisi
            ),
            kazanma_orani=kazanma_orani,
            ortalama_net_getiri_orani=(
                ortalama_net_getiri_orani
            ),
            bilesik_getiri_orani=(
                bilesik_getiri_orani
            ),
            kar_faktoru=(
                self._kar_faktorunu_hesapla(
                    net_getiriler
                )
            ),
            yil_basi_sermayesi=(
                yil_basi_sermayesi
            ),
            yil_sonu_sermayesi=(
                yil_sonu_sermayesi
            ),
        )

    def _cikis_nedeni_performansi_olustur(
        self,
        cikis_nedeni: str,
        islemler: tuple[
            BacktestTrade,
            ...,
        ],
        toplam_islem_sayisi: int,
        pozisyon_orani: float,
    ) -> ExitReasonPerformance:
        net_getiriler = tuple(
            islem.net_getiri_orani
            for islem in islemler
        )

        (
            kazanan_sayisi,
            kaybeden_sayisi,
            basabas_sayisi,
        ) = self._sonuc_sayilarini_hesapla(
            net_getiriler
        )

        islem_sayisi = len(
            net_getiriler
        )

        bilesik_carpan = 1.0

        for net_getiri_orani in net_getiriler:
            bilesik_carpan *= (
                1.0
                + net_getiri_orani
                * pozisyon_orani
            )

        return ExitReasonPerformance(
            cikis_nedeni=cikis_nedeni,
            islem_sayisi=islem_sayisi,
            toplam_islem_orani=(
                islem_sayisi
                / toplam_islem_sayisi
            ),
            kazanan_islem_sayisi=(
                kazanan_sayisi
            ),
            kaybeden_islem_sayisi=(
                kaybeden_sayisi
            ),
            basabas_islem_sayisi=(
                basabas_sayisi
            ),
            kazanma_orani=(
                kazanan_sayisi
                / islem_sayisi
            ),
            ortalama_net_getiri_orani=(
                sum(
                    net_getiriler
                )
                / islem_sayisi
            ),
            bilesik_getiri_orani=(
                bilesik_carpan
                - 1.0
            ),
        )

    @staticmethod
    def _sonuc_sayilarini_hesapla(
        net_getiriler: tuple[
            float,
            ...,
        ],
    ) -> tuple[int, int, int]:
        kazanan_sayisi = sum(
            1
            for getiri in net_getiriler
            if getiri > 0
        )

        kaybeden_sayisi = sum(
            1
            for getiri in net_getiriler
            if getiri < 0
        )

        basabas_sayisi = (
            len(
                net_getiriler
            )
            - kazanan_sayisi
            - kaybeden_sayisi
        )

        return (
            kazanan_sayisi,
            kaybeden_sayisi,
            basabas_sayisi,
        )

    @staticmethod
    def _kar_faktorunu_hesapla(
        net_getiriler: tuple[
            float,
            ...,
        ],
    ) -> float | None:
        toplam_kar = sum(
            getiri
            for getiri in net_getiriler
            if getiri > 0
        )

        toplam_kayip = abs(
            sum(
                getiri
                for getiri in net_getiriler
                if getiri < 0
            )
        )

        if toplam_kayip == 0:
            return None

        return (
            toplam_kar
            / toplam_kayip
        )