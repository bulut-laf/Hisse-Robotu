from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite
from typing import Iterable

from .backtest_models import BacktestTrade


class EquityCurveError(ValueError):
    """Özsermaye eğrisi hesaplama hatası."""


@dataclass(frozen=True)
class EquityPoint:
    """Tamamlanan bir işlem sonrasındaki sermaye noktası."""

    islem_sirasi: int
    tarih: date
    sembol: str
    onceki_sermaye: float
    sonraki_sermaye: float
    net_getiri_orani: float
    uygulanan_getiri_orani: float
    zirve_sermayesi: float
    dusus_orani: float


@dataclass(frozen=True)
class DrawdownPeriod:
    """Bir sermaye zirvesinden toparlanmaya kadar olan düşüş dönemi."""

    zirve_tarihi: date
    dip_tarihi: date
    toparlanma_tarihi: date | None
    zirve_sermayesi: float
    dip_sermayesi: float
    dusus_orani: float
    zirve_altinda_gun_sayisi: int

    @property
    def toparlandi_mi(self) -> bool:
        return self.toparlanma_tarihi is not None


@dataclass(frozen=True)
class EquityCurveReport:
    """Backtest işlemlerinden üretilen özsermaye raporu."""

    baslangic_sermayesi: float
    bitis_sermayesi: float
    toplam_bilesik_getiri_orani: float
    noktalar: tuple[EquityPoint, ...]
    dusus_donemleri: tuple[DrawdownPeriod, ...]
    maksimum_dusus_orani: float
    maksimum_dusus_donemi: DrawdownPeriod | None
    en_uzun_dusus_donemi: DrawdownPeriod | None

    @property
    def islem_sayisi(self) -> int:
        return len(self.noktalar)

    @property
    def dusus_donemi_sayisi(self) -> int:
        return len(self.dusus_donemleri)


@dataclass
class _OpenDrawdown:
    """Hesaplama sırasında kullanılan açık düşüş durumu."""

    zirve_tarihi: date
    zirve_sermayesi: float
    dip_tarihi: date
    dip_sermayesi: float


class EquityCurveAnalyzer:
    """
    Tamamlanmış backtest işlemlerinden özsermaye eğrisi
    ve sermaye düşüş dönemleri oluşturur.

    İşlemler çıkış tarihine göre sıralanır. Getiri,
    işlemin kapandığı anda sermayeye uygulanır.
    """

    def analiz_et(
        self,
        islemler: Iterable[BacktestTrade],
        baslangic_sermayesi: float = 100_000.0,
        pozisyon_orani: float = 1.0,
    ) -> EquityCurveReport:
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
            return EquityCurveReport(
                baslangic_sermayesi=baslangic_sermayesi,
                bitis_sermayesi=baslangic_sermayesi,
                toplam_bilesik_getiri_orani=0.0,
                noktalar=(),
                dusus_donemleri=(),
                maksimum_dusus_orani=0.0,
                maksimum_dusus_donemi=None,
                en_uzun_dusus_donemi=None,
            )

        self._islemleri_dogrula(
            sirali_islemler
        )

        sermaye = baslangic_sermayesi

        ilk_tarih = min(
            islem.giris_tarihi
            for islem in sirali_islemler
        )

        zirve_sermayesi = baslangic_sermayesi
        zirve_tarihi = ilk_tarih

        noktalar: list[EquityPoint] = []
        dusus_donemleri: list[DrawdownPeriod] = []

        acik_dusus: _OpenDrawdown | None = None

        for sira, islem in enumerate(
            sirali_islemler,
            start=1,
        ):
            onceki_sermaye = sermaye

            uygulanan_getiri_orani = (
                islem.net_getiri_orani
                * pozisyon_orani
            )

            getiri_carpani = (
                1.0
                + uygulanan_getiri_orani
            )

            if getiri_carpani <= 0:
                raise EquityCurveError(
                    "İşlem getirisi sermayeyi sıfır "
                    "veya negatif değere düşürüyor."
                )

            sermaye *= getiri_carpani

            if sermaye >= zirve_sermayesi:
                if acik_dusus is not None:
                    dusus_donemleri.append(
                        self._dusus_donemini_kapat(
                            acik_dusus=acik_dusus,
                            toparlanma_tarihi=(
                                islem.cikis_tarihi
                            ),
                        )
                    )

                    acik_dusus = None

                zirve_sermayesi = sermaye
                zirve_tarihi = islem.cikis_tarihi
                dusus_orani = 0.0

            else:
                dusus_orani = (
                    1.0
                    - sermaye
                    / zirve_sermayesi
                )

                if acik_dusus is None:
                    acik_dusus = _OpenDrawdown(
                        zirve_tarihi=zirve_tarihi,
                        zirve_sermayesi=(
                            zirve_sermayesi
                        ),
                        dip_tarihi=(
                            islem.cikis_tarihi
                        ),
                        dip_sermayesi=sermaye,
                    )

                elif sermaye < acik_dusus.dip_sermayesi:
                    acik_dusus.dip_tarihi = (
                        islem.cikis_tarihi
                    )
                    acik_dusus.dip_sermayesi = sermaye

            noktalar.append(
                EquityPoint(
                    islem_sirasi=sira,
                    tarih=islem.cikis_tarihi,
                    sembol=islem.sembol,
                    onceki_sermaye=(
                        onceki_sermaye
                    ),
                    sonraki_sermaye=sermaye,
                    net_getiri_orani=(
                        islem.net_getiri_orani
                    ),
                    uygulanan_getiri_orani=(
                        uygulanan_getiri_orani
                    ),
                    zirve_sermayesi=(
                        zirve_sermayesi
                    ),
                    dusus_orani=dusus_orani,
                )
            )

        if acik_dusus is not None:
            son_tarih = (
                sirali_islemler[-1]
                .cikis_tarihi
            )

            dusus_donemleri.append(
                self._acik_dusus_donemini_olustur(
                    acik_dusus=acik_dusus,
                    son_tarih=son_tarih,
                )
            )

        dusus_donemleri_tuple = tuple(
            dusus_donemleri
        )

        maksimum_dusus_donemi = (
            max(
                dusus_donemleri_tuple,
                key=lambda donem: (
                    donem.dusus_orani
                ),
            )
            if dusus_donemleri_tuple
            else None
        )

        en_uzun_dusus_donemi = (
            max(
                dusus_donemleri_tuple,
                key=lambda donem: (
                    donem.zirve_altinda_gun_sayisi
                ),
            )
            if dusus_donemleri_tuple
            else None
        )

        maksimum_dusus_orani = (
            maksimum_dusus_donemi.dusus_orani
            if maksimum_dusus_donemi is not None
            else 0.0
        )

        toplam_bilesik_getiri_orani = (
            sermaye
            / baslangic_sermayesi
            - 1.0
        )

        return EquityCurveReport(
            baslangic_sermayesi=(
                baslangic_sermayesi
            ),
            bitis_sermayesi=sermaye,
            toplam_bilesik_getiri_orani=(
                toplam_bilesik_getiri_orani
            ),
            noktalar=tuple(
                noktalar
            ),
            dusus_donemleri=(
                dusus_donemleri_tuple
            ),
            maksimum_dusus_orani=(
                maksimum_dusus_orani
            ),
            maksimum_dusus_donemi=(
                maksimum_dusus_donemi
            ),
            en_uzun_dusus_donemi=(
                en_uzun_dusus_donemi
            ),
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
            raise EquityCurveError(
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
            raise EquityCurveError(
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
                raise EquityCurveError(
                    "İşlem net getirisi sonlu "
                    "olmalıdır."
                )

            if (
                islem.cikis_tarihi
                < islem.giris_tarihi
            ):
                raise EquityCurveError(
                    "İşlem çıkış tarihi giriş "
                    "tarihinden önce olamaz."
                )

    @staticmethod
    def _dusus_donemini_kapat(
        acik_dusus: _OpenDrawdown,
        toparlanma_tarihi: date,
    ) -> DrawdownPeriod:
        dusus_orani = (
            1.0
            - acik_dusus.dip_sermayesi
            / acik_dusus.zirve_sermayesi
        )

        return DrawdownPeriod(
            zirve_tarihi=(
                acik_dusus.zirve_tarihi
            ),
            dip_tarihi=(
                acik_dusus.dip_tarihi
            ),
            toparlanma_tarihi=(
                toparlanma_tarihi
            ),
            zirve_sermayesi=(
                acik_dusus.zirve_sermayesi
            ),
            dip_sermayesi=(
                acik_dusus.dip_sermayesi
            ),
            dusus_orani=dusus_orani,
            zirve_altinda_gun_sayisi=(
                toparlanma_tarihi
                - acik_dusus.zirve_tarihi
            ).days,
        )

    @staticmethod
    def _acik_dusus_donemini_olustur(
        acik_dusus: _OpenDrawdown,
        son_tarih: date,
    ) -> DrawdownPeriod:
        dusus_orani = (
            1.0
            - acik_dusus.dip_sermayesi
            / acik_dusus.zirve_sermayesi
        )

        return DrawdownPeriod(
            zirve_tarihi=(
                acik_dusus.zirve_tarihi
            ),
            dip_tarihi=(
                acik_dusus.dip_tarihi
            ),
            toparlanma_tarihi=None,
            zirve_sermayesi=(
                acik_dusus.zirve_sermayesi
            ),
            dip_sermayesi=(
                acik_dusus.dip_sermayesi
            ),
            dusus_orani=dusus_orani,
            zirve_altinda_gun_sayisi=(
                son_tarih
                - acik_dusus.zirve_tarihi
            ).days,
        )