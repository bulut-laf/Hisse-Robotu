from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

import pandas as pd

from ..data.market_data import MarketDataError, fiyat_verisi_getir
from ..ui.backtest_dashboard import (
    BacktestDashboardService,
    DashboardBacktestRequest,
    DashboardResult,
)
from .backtest_service import BacktestServiceError, StockBacktestService


YUKSEK_DAHA_IYI = "yuksek"
DUSUK_DAHA_IYI = "dusuk"
NOTR = "notr"
BAZ_ANALIZ = "baz"
KARSILASTIRMA_ANALIZI = "karsilastirma"
ESIT = "esit"


class SameDataComparisonError(RuntimeError):
    """Aynı veri karşılaştırması hazırlanamadığında oluşur."""


class DashboardRunnerProtocol(Protocol):
    def calistir(self, istek: DashboardBacktestRequest) -> DashboardResult:
        ...


VeriGetirici = Callable[..., pd.DataFrame]
DashboardRunnerFactory = Callable[[pd.DataFrame], DashboardRunnerProtocol]


@dataclass(frozen=True)
class SameDataComparisonMetric:
    """Aynı veri üzerinde iki ayarın tek performans ölçütündeki farkı."""

    anahtar: str
    etiket: str
    birim: str
    baz_deger: float
    karsilastirma_degeri: float
    fark: float
    iyilik_yonu: str
    lider: str


@dataclass(frozen=True)
class SameDataComparisonResult:
    """Tek fiyat anlık görüntüsüyle üretilen iki backtest sonucu."""

    baz_sonuc: DashboardResult
    karsilastirma_sonucu: DashboardResult
    veri_kimligi: str
    fiyat_donemi: str
    fiyat_bar_sayisi: int
    metrikler: tuple[SameDataComparisonMetric, ...]

    @property
    def ayar_kimlikleri_farkli(self) -> bool:
        return (
            self.baz_sonuc.ozet.ayar_kimligi
            != self.karsilastirma_sonucu.ozet.ayar_kimligi
        )


class SameDataComparisonService:
    """Fiyat verisini bir kez alır ve iki ayarı aynı kopyada çalıştırır."""

    def __init__(
        self,
        veri_getirici: VeriGetirici = fiyat_verisi_getir,
        dashboard_uretici: DashboardRunnerFactory | None = None,
    ) -> None:
        if not callable(veri_getirici):
            raise TypeError("Veri getirici çağrılabilir olmalıdır.")
        if dashboard_uretici is not None and not callable(dashboard_uretici):
            raise TypeError("Dashboard üretici çağrılabilir olmalıdır.")

        self._veri_getirici = veri_getirici
        self._dashboard_uretici = (
            dashboard_uretici
            if dashboard_uretici is not None
            else self._varsayilan_dashboard_uret
        )

    def calistir(
        self,
        baz_istek: DashboardBacktestRequest,
        karsilastirma_istegi: DashboardBacktestRequest,
    ) -> SameDataComparisonResult:
        self._istekleri_dogrula(baz_istek, karsilastirma_istegi)

        try:
            ham_veri = self._veri_getirici(
                sembol=baz_istek.sembol,
                islem_gunu=baz_istek.islem_gunu,
                indirme_donemi=baz_istek.indirme_donemi,
                yalnizca_tamamlanmis_gunler=True,
            )
        except (MarketDataError, ValueError, TypeError) as hata:
            raise SameDataComparisonError(
                f"{baz_istek.sembol} fiyat anlık görüntüsü alınamadı: {hata}"
            ) from hata

        if not isinstance(ham_veri, pd.DataFrame):
            raise SameDataComparisonError(
                "Veri getirici pandas DataFrame döndürmelidir."
            )
        if ham_veri.empty:
            raise SameDataComparisonError("Fiyat anlık görüntüsü boş olamaz.")

        anlik_goruntu = ham_veri.copy(deep=True)

        baz_veri = anlik_goruntu.copy(deep=True)
        karsilastirma_verisi = anlik_goruntu.copy(deep=True)

        try:
            baz_calistirici = self._dashboard_uretici(baz_veri)
            karsilastirma_calistiricisi = self._dashboard_uretici(
                karsilastirma_verisi
            )
            baz_sonuc = baz_calistirici.calistir(baz_istek)
            karsilastirma_sonucu = karsilastirma_calistiricisi.calistir(
                karsilastirma_istegi
            )
        except (BacktestServiceError, ValueError, TypeError) as hata:
            raise SameDataComparisonError(
                f"Aynı veri karşılaştırması çalıştırılamadı: {hata}"
            ) from hata

        baz_ozet = baz_sonuc.ozet
        karsilastirma_ozeti = karsilastirma_sonucu.ozet
        if baz_ozet.veri_kimligi != karsilastirma_ozeti.veri_kimligi:
            raise SameDataComparisonError(
                "Karşılaştırma sonuçları aynı veri kimliğini üretmedi."
            )
        if baz_ozet.fiyat_donemi != karsilastirma_ozeti.fiyat_donemi:
            raise SameDataComparisonError(
                "Karşılaştırma sonuçlarının fiyat dönemleri farklı."
            )
        if baz_ozet.fiyat_bar_sayisi != karsilastirma_ozeti.fiyat_bar_sayisi:
            raise SameDataComparisonError(
                "Karşılaştırma sonuçlarının fiyat barı sayıları farklı."
            )

        return SameDataComparisonResult(
            baz_sonuc=baz_sonuc,
            karsilastirma_sonucu=karsilastirma_sonucu,
            veri_kimligi=baz_ozet.veri_kimligi,
            fiyat_donemi=baz_ozet.fiyat_donemi,
            fiyat_bar_sayisi=baz_ozet.fiyat_bar_sayisi,
            metrikler=_metrikleri_olustur(
                baz_sonuc,
                karsilastirma_sonucu,
            ),
        )

    @staticmethod
    def _istekleri_dogrula(
        baz_istek: DashboardBacktestRequest,
        karsilastirma_istegi: DashboardBacktestRequest,
    ) -> None:
        if not isinstance(baz_istek, DashboardBacktestRequest) or not isinstance(
            karsilastirma_istegi, DashboardBacktestRequest
        ):
            raise TypeError(
                "Karşılaştırma için iki DashboardBacktestRequest gereklidir."
            )
        if baz_istek.sembol != karsilastirma_istegi.sembol:
            raise ValueError("Aynı veri karşılaştırmasında semboller aynı olmalıdır.")
        if baz_istek.islem_gunu != karsilastirma_istegi.islem_gunu:
            raise ValueError(
                "Aynı veri karşılaştırmasında işlem günü sınırı aynı olmalıdır."
            )
        if baz_istek.indirme_donemi != karsilastirma_istegi.indirme_donemi:
            raise ValueError(
                "Aynı veri karşılaştırmasında indirme dönemi aynı olmalıdır."
            )
        if (
            baz_istek.profil_olustur().ayar_kimligi
            == karsilastirma_istegi.profil_olustur().ayar_kimligi
        ):
            raise ValueError(
                "Karşılaştırılan ayarlardan en az biri farklı olmalıdır."
            )

    @staticmethod
    def _varsayilan_dashboard_uret(
        anlik_goruntu: pd.DataFrame,
    ) -> BacktestDashboardService:
        sabit_veri = anlik_goruntu.copy(deep=True)

        def anlik_goruntu_getir(**_: object) -> pd.DataFrame:
            return sabit_veri.copy(deep=True)

        return BacktestDashboardService(
            StockBacktestService(veri_getirici=anlik_goruntu_getir)
        )


def _metrikleri_olustur(
    baz: DashboardResult,
    karsilastirma: DashboardResult,
) -> tuple[SameDataComparisonMetric, ...]:
    baz_ozet = baz.ozet
    ikinci_ozet = karsilastirma.ozet
    metrikler = [
        _metrik(
            "bitis_sermayesi",
            "Bitiş sermayesi",
            "para",
            baz_ozet.bitis_sermayesi,
            ikinci_ozet.bitis_sermayesi,
            YUKSEK_DAHA_IYI,
        ),
        _metrik(
            "toplam_getiri_yuzde",
            "Toplam getiri",
            "yuzde",
            baz_ozet.toplam_getiri_yuzde,
            ikinci_ozet.toplam_getiri_yuzde,
            YUKSEK_DAHA_IYI,
        ),
        _metrik(
            "maksimum_dusus_yuzde",
            "Maksimum düşüş",
            "yuzde",
            baz_ozet.maksimum_dusus_yuzde,
            ikinci_ozet.maksimum_dusus_yuzde,
            DUSUK_DAHA_IYI,
        ),
        _metrik(
            "guncel_dusus_yuzde",
            "Güncel düşüş",
            "yuzde",
            baz_ozet.guncel_dusus_yuzde,
            ikinci_ozet.guncel_dusus_yuzde,
            DUSUK_DAHA_IYI,
        ),
        _metrik(
            "tamamlanan_islem_sayisi",
            "Tamamlanan işlem",
            "sayi",
            float(baz_ozet.tamamlanan_islem_sayisi),
            float(ikinci_ozet.tamamlanan_islem_sayisi),
            NOTR,
        ),
        _metrik(
            "atlanan_sinyal_sayisi",
            "Atlanan sinyal",
            "sayi",
            float(baz_ozet.atlanan_sinyal_sayisi),
            float(ikinci_ozet.atlanan_sinyal_sayisi),
            NOTR,
        ),
        _metrik(
            "getiri_dusus_orani",
            "Getiri / maksimum düşüş",
            "oran",
            _getiri_dusus_orani(baz_ozet),
            _getiri_dusus_orani(ikinci_ozet),
            YUKSEK_DAHA_IYI,
        ),
        _metrik(
            "kazanma_yuzde",
            "Kazanma oranı",
            "yuzde",
            baz_ozet.kazanma_yuzde,
            ikinci_ozet.kazanma_yuzde,
            YUKSEK_DAHA_IYI,
        ),
    ]
    if baz_ozet.kar_faktoru is not None and ikinci_ozet.kar_faktoru is not None:
        metrikler.insert(
            4,
            _metrik(
                "kar_faktoru",
                "Kâr faktörü",
                "oran",
                baz_ozet.kar_faktoru,
                ikinci_ozet.kar_faktoru,
                YUKSEK_DAHA_IYI,
            ),
        )
    return tuple(metrikler)


def _getiri_dusus_orani(ozet: object) -> float:
    maksimum_dusus = float(getattr(ozet, "maksimum_dusus_yuzde"))
    if maksimum_dusus <= 0:
        return 0.0
    return float(getattr(ozet, "toplam_getiri_yuzde")) / maksimum_dusus


def _metrik(
    anahtar: str,
    etiket: str,
    birim: str,
    baz_deger: float,
    karsilastirma_degeri: float,
    iyilik_yonu: str,
) -> SameDataComparisonMetric:
    fark = karsilastirma_degeri - baz_deger
    return SameDataComparisonMetric(
        anahtar=anahtar,
        etiket=etiket,
        birim=birim,
        baz_deger=baz_deger,
        karsilastirma_degeri=karsilastirma_degeri,
        fark=fark,
        iyilik_yonu=iyilik_yonu,
        lider=_lider_belirle(
            baz_deger,
            karsilastirma_degeri,
            iyilik_yonu,
        ),
    )


def _lider_belirle(baz: float, ikinci: float, iyilik_yonu: str) -> str:
    if iyilik_yonu == NOTR:
        return ESIT
    if abs(ikinci - baz) < 1e-12:
        return ESIT
    if iyilik_yonu == YUKSEK_DAHA_IYI:
        return KARSILASTIRMA_ANALIZI if ikinci > baz else BAZ_ANALIZ
    if iyilik_yonu == DUSUK_DAHA_IYI:
        return KARSILASTIRMA_ANALIZI if ikinci < baz else BAZ_ANALIZ
    raise ValueError("Bilinmeyen metrik iyilik yönü.")
