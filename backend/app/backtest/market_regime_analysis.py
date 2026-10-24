from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from math import isfinite
from typing import Iterable

import pandas as pd

from ..indicators.technical_indicators import atr, ema
from .backtest_models import (
    BacktestConfig,
    BacktestMetrics,
    BacktestTrade,
)


TREND_YUKSELIS = "Yükseliş Trendi"
TREND_YATAY = "Yatay Piyasa"
TREND_DUSUS = "Düşüş Trendi"

VOLATILITE_NORMAL = "Normal Volatilite"
VOLATILITE_YUKSEK = "Yüksek Volatilite"

TREND_SIRASI = (
    TREND_YUKSELIS,
    TREND_YATAY,
    TREND_DUSUS,
)

VOLATILITE_SIRASI = (
    VOLATILITE_NORMAL,
    VOLATILITE_YUKSEK,
)


class MarketRegimeAnalysisError(ValueError):
    """Piyasa rejimi analizinde oluşan veri veya ayar hatası."""


@dataclass(frozen=True)
class MarketRegimeConfig:
    """Açıklanabilir trend ve volatilite sınıflandırma ayarları."""

    hizli_ema_periyodu: int = 21
    yavas_ema_periyodu: int = 55
    egim_bakisi: int = 10
    minimum_ema_farki_orani: float = 0.005
    atr_periyodu: int = 14
    volatilite_bakisi: int = 42
    yuksek_volatilite_carpani: float = 1.0

    def __post_init__(self) -> None:
        if self.hizli_ema_periyodu < 2:
            raise ValueError(
                "Hızlı EMA periyodu en az 2 olmalıdır."
            )

        if self.yavas_ema_periyodu <= self.hizli_ema_periyodu:
            raise ValueError(
                "Yavaş EMA periyodu hızlı EMA periyodundan "
                "büyük olmalıdır."
            )

        if self.egim_bakisi < 1:
            raise ValueError(
                "Eğim bakışı en az 1 olmalıdır."
            )

        if (
            not isfinite(self.minimum_ema_farki_orani)
            or not 0 <= self.minimum_ema_farki_orani < 1
        ):
            raise ValueError(
                "Minimum EMA farkı oranı 0 ile 1 arasında "
                "olmalıdır."
            )

        if self.atr_periyodu < 2:
            raise ValueError(
                "ATR periyodu en az 2 olmalıdır."
            )

        if self.volatilite_bakisi < 2:
            raise ValueError(
                "Volatilite bakışı en az 2 olmalıdır."
            )

        if (
            not isfinite(self.yuksek_volatilite_carpani)
            or self.yuksek_volatilite_carpani <= 0
        ):
            raise ValueError(
                "Yüksek volatilite çarpanı pozitif ve sonlu "
                "olmalıdır."
            )


@dataclass(frozen=True)
class MarketRegimePoint:
    """Tek bir işlem gününün geçmişe dönük piyasa rejimi."""

    tarih: date
    kapanis: float
    hizli_ema: float
    yavas_ema: float
    atr_orani: float
    volatilite_esigi_orani: float
    trend_rejimi: str
    volatilite_rejimi: str

    @property
    def birlesik_rejim(self) -> str:
        return (
            f"{self.trend_rejimi} / "
            f"{self.volatilite_rejimi}"
        )


@dataclass(frozen=True)
class RegimeDayCount:
    """Bir rejimin sınıflandırılmış işlem günlerindeki dağılımı."""

    rejim_adi: str
    gun_sayisi: int
    toplam_gun_orani: float


@dataclass(frozen=True)
class RegimePerformance:
    """Bir rejime atanmış işlemlerin performans özeti."""

    rejim_adi: str
    islem_sayisi: int
    toplam_islem_orani: float
    kazanan_islem_sayisi: int
    kaybeden_islem_sayisi: int
    basabas_islem_sayisi: int
    kazanma_orani: float
    ortalama_net_getiri_orani: float
    toplam_net_getiri_orani: float
    kar_faktoru: float | None
    maksimum_ardisik_kayip: int


@dataclass(frozen=True)
class MarketRegimeReport:
    """Günlük rejim sınıflandırması ve rejim bazlı işlem sonuçları."""

    sembol: str
    yapilandirma: MarketRegimeConfig
    gunluk_noktalar: tuple[MarketRegimePoint, ...]
    trend_gun_dagilimi: tuple[RegimeDayCount, ...]
    volatilite_gun_dagilimi: tuple[RegimeDayCount, ...]
    trend_performanslari: tuple[RegimePerformance, ...]
    volatilite_performanslari: tuple[RegimePerformance, ...]
    birlesik_performanslar: tuple[RegimePerformance, ...]
    toplam_islem_sayisi: int
    siniflandirilan_islem_sayisi: int
    siniflandirilamayan_islem_sayisi: int
    en_iyi_birlesik_rejim: RegimePerformance | None
    en_zayif_birlesik_rejim: RegimePerformance | None

    @property
    def siniflandirma_orani(self) -> float:
        if self.toplam_islem_sayisi == 0:
            return 0.0

        return (
            self.siniflandirilan_islem_sayisi
            / self.toplam_islem_sayisi
        )

    @property
    def siniflandirilan_gun_sayisi(self) -> int:
        return len(self.gunluk_noktalar)

    @property
    def ilk_rejim_tarihi(self) -> date | None:
        if not self.gunluk_noktalar:
            return None

        return self.gunluk_noktalar[0].tarih

    @property
    def son_rejim_tarihi(self) -> date | None:
        if not self.gunluk_noktalar:
            return None

        return self.gunluk_noktalar[-1].tarih


class MarketRegimeAnalyzer:
    """
    Günleri trend ve volatilite rejimlerine ayırır; tamamlanan
    işlemleri sinyal gününde bilinen rejime göre performanslandırır.

    Trend kuralı, kapanış ile hızlı/yavaş EMA sıralamasını, hızlı
    EMA eğimini ve iki EMA arasındaki minimum farkı birlikte kullanır.
    Volatilite kuralı, ATR oranını yalnızca geçmiş ve güncel verilerden
    oluşan hareketli medyanla karşılaştırır. Gelecek veri kullanılmaz.
    """

    def analiz_et(
        self,
        sembol: str,
        fiyat_verisi: pd.DataFrame,
        islemler: Iterable[BacktestTrade],
        backtest_yapilandirmasi: BacktestConfig,
        yapilandirma: MarketRegimeConfig | None = None,
    ) -> MarketRegimeReport:
        ayarlar = (
            yapilandirma
            if yapilandirma is not None
            else MarketRegimeConfig()
        )
        temiz_sembol = self._sembolu_hazirla(sembol)
        hazir_veri = self._fiyat_verisini_hazirla(fiyat_verisi)
        gunluk_noktalar = self._gunluk_rejimleri_hesapla(
            fiyat_verisi=hazir_veri,
            yapilandirma=ayarlar,
        )
        nokta_haritasi = {
            nokta.tarih: nokta
            for nokta in gunluk_noktalar
        }
        hedef_islemler = tuple(
            sorted(
                (
                    islem
                    for islem in tuple(islemler)
                    if islem.sembol == temiz_sembol
                ),
                key=lambda islem: (
                    islem.sinyal_tarihi,
                    islem.giris_tarihi,
                    islem.cikis_tarihi,
                ),
            )
        )

        trend_gruplari: dict[str, list[BacktestTrade]] = {
            rejim: []
            for rejim in TREND_SIRASI
        }
        volatilite_gruplari: dict[str, list[BacktestTrade]] = {
            rejim: []
            for rejim in VOLATILITE_SIRASI
        }
        birlesik_gruplar: dict[str, list[BacktestTrade]] = {
            f"{trend} / {volatilite}": []
            for trend in TREND_SIRASI
            for volatilite in VOLATILITE_SIRASI
        }
        siniflandirilan_islem_sayisi = 0

        for islem in hedef_islemler:
            nokta = nokta_haritasi.get(islem.sinyal_tarihi)

            if nokta is None:
                continue

            siniflandirilan_islem_sayisi += 1
            trend_gruplari[nokta.trend_rejimi].append(islem)
            volatilite_gruplari[nokta.volatilite_rejimi].append(islem)
            birlesik_gruplar[nokta.birlesik_rejim].append(islem)

        trend_performanslari = tuple(
            self._performans_olustur(
                rejim_adi=rejim,
                islemler=trend_gruplari[rejim],
                toplam_islem_sayisi=siniflandirilan_islem_sayisi,
                backtest_yapilandirmasi=backtest_yapilandirmasi,
            )
            for rejim in TREND_SIRASI
        )
        volatilite_performanslari = tuple(
            self._performans_olustur(
                rejim_adi=rejim,
                islemler=volatilite_gruplari[rejim],
                toplam_islem_sayisi=siniflandirilan_islem_sayisi,
                backtest_yapilandirmasi=backtest_yapilandirmasi,
            )
            for rejim in VOLATILITE_SIRASI
        )
        birlesik_performanslar = tuple(
            self._performans_olustur(
                rejim_adi=rejim,
                islemler=birlesik_gruplar[rejim],
                toplam_islem_sayisi=siniflandirilan_islem_sayisi,
                backtest_yapilandirmasi=backtest_yapilandirmasi,
            )
            for rejim in birlesik_gruplar
        )
        etkin_birlesik_rejimler = tuple(
            performans
            for performans in birlesik_performanslar
            if performans.islem_sayisi > 0
        )

        return MarketRegimeReport(
            sembol=temiz_sembol,
            yapilandirma=ayarlar,
            gunluk_noktalar=gunluk_noktalar,
            trend_gun_dagilimi=self._gun_dagilimini_olustur(
                gunluk_noktalar=gunluk_noktalar,
                alan_adi="trend_rejimi",
                rejim_sirasi=TREND_SIRASI,
            ),
            volatilite_gun_dagilimi=self._gun_dagilimini_olustur(
                gunluk_noktalar=gunluk_noktalar,
                alan_adi="volatilite_rejimi",
                rejim_sirasi=VOLATILITE_SIRASI,
            ),
            trend_performanslari=trend_performanslari,
            volatilite_performanslari=(
                volatilite_performanslari
            ),
            birlesik_performanslar=birlesik_performanslar,
            toplam_islem_sayisi=len(hedef_islemler),
            siniflandirilan_islem_sayisi=(
                siniflandirilan_islem_sayisi
            ),
            siniflandirilamayan_islem_sayisi=(
                len(hedef_islemler)
                - siniflandirilan_islem_sayisi
            ),
            en_iyi_birlesik_rejim=(
                max(
                    etkin_birlesik_rejimler,
                    key=lambda sonuc: (
                        sonuc.toplam_net_getiri_orani,
                        sonuc.islem_sayisi,
                    ),
                )
                if etkin_birlesik_rejimler
                else None
            ),
            en_zayif_birlesik_rejim=(
                min(
                    etkin_birlesik_rejimler,
                    key=lambda sonuc: (
                        sonuc.toplam_net_getiri_orani,
                        -sonuc.islem_sayisi,
                    ),
                )
                if etkin_birlesik_rejimler
                else None
            ),
        )

    @staticmethod
    def _sembolu_hazirla(sembol: str) -> str:
        temiz_sembol = sembol.strip().upper()

        if not temiz_sembol:
            raise MarketRegimeAnalysisError(
                "Hisse sembolü boş olamaz."
            )

        if "." not in temiz_sembol:
            temiz_sembol += ".IS"

        return temiz_sembol

    @staticmethod
    def _fiyat_verisini_hazirla(
        fiyat_verisi: pd.DataFrame,
    ) -> pd.DataFrame:
        if not isinstance(fiyat_verisi, pd.DataFrame):
            raise MarketRegimeAnalysisError(
                "Fiyat verisi pandas DataFrame olmalıdır."
            )

        if fiyat_verisi.empty:
            raise MarketRegimeAnalysisError(
                "Fiyat verisi boş olamaz."
            )

        gerekli_sutunlar = {"High", "Low", "Close"}
        eksik_sutunlar = gerekli_sutunlar.difference(
            fiyat_verisi.columns
        )

        if eksik_sutunlar:
            raise MarketRegimeAnalysisError(
                "Eksik fiyat sütunları: "
                + ", ".join(sorted(eksik_sutunlar))
            )

        kopya = fiyat_verisi.copy()
        tarihler = pd.to_datetime(kopya.index, errors="coerce")

        if tarihler.isna().any():
            raise MarketRegimeAnalysisError(
                "Fiyat verisinde geçersiz tarihler var."
            )

        if tarihler.tz is not None:
            tarihler = tarihler.tz_localize(None)

        kopya.index = tarihler.normalize()
        kopya = kopya.sort_index()

        if kopya.index.has_duplicates:
            raise MarketRegimeAnalysisError(
                "Fiyat verisinde tekrarlanan tarihler var."
            )

        for sutun in gerekli_sutunlar:
            kopya[sutun] = pd.to_numeric(
                kopya[sutun],
                errors="coerce",
            )

        if kopya[list(gerekli_sutunlar)].isna().any().any():
            raise MarketRegimeAnalysisError(
                "Fiyat verisinde boş veya sayısal olmayan "
                "değerler var."
            )

        if (kopya[list(gerekli_sutunlar)] <= 0).any().any():
            raise MarketRegimeAnalysisError(
                "Fiyat değerleri pozitif olmalıdır."
            )

        if (kopya["High"] < kopya["Low"]).any():
            raise MarketRegimeAnalysisError(
                "En yüksek fiyat en düşük fiyattan küçük olamaz."
            )

        if (
            (kopya["High"] < kopya["Close"]).any()
            or (kopya["Low"] > kopya["Close"]).any()
        ):
            raise MarketRegimeAnalysisError(
                "Kapanış fiyatı günlük yüksek-düşük aralığında "
                "olmalıdır."
            )

        return kopya

    @staticmethod
    def _gunluk_rejimleri_hesapla(
        fiyat_verisi: pd.DataFrame,
        yapilandirma: MarketRegimeConfig,
    ) -> tuple[MarketRegimePoint, ...]:
        kapanis = fiyat_verisi["Close"]
        hizli_ema = ema(
            kapanis,
            yapilandirma.hizli_ema_periyodu,
        )
        yavas_ema = ema(
            kapanis,
            yapilandirma.yavas_ema_periyodu,
        )
        hizli_ema_egimi = (
            hizli_ema
            - hizli_ema.shift(yapilandirma.egim_bakisi)
        )
        ema_farki_orani = (
            (hizli_ema - yavas_ema).abs()
            / kapanis
        )
        atr_orani = (
            atr(
                fiyat_verisi,
                periyot=yapilandirma.atr_periyodu,
            )
            / kapanis
        )
        volatilite_esigi = atr_orani.rolling(
            window=yapilandirma.volatilite_bakisi,
            min_periods=yapilandirma.volatilite_bakisi,
        ).median()

        hesaplama = pd.DataFrame(
            {
                "Close": kapanis,
                "HizliEMA": hizli_ema,
                "YavasEMA": yavas_ema,
                "HizliEMAEgimi": hizli_ema_egimi,
                "EMAFarkiOrani": ema_farki_orani,
                "ATROrani": atr_orani,
                "VolatiliteEsigi": volatilite_esigi,
            },
            index=fiyat_verisi.index,
        ).dropna()
        noktalar: list[MarketRegimePoint] = []

        for zaman, satir in hesaplama.iterrows():
            kapanis_degeri = float(satir["Close"])
            hizli_ema_degeri = float(satir["HizliEMA"])
            yavas_ema_degeri = float(satir["YavasEMA"])
            egim = float(satir["HizliEMAEgimi"])
            ema_farki = float(satir["EMAFarkiOrani"])
            atr_degeri = float(satir["ATROrani"])
            volatilite_esigi_degeri = float(
                satir["VolatiliteEsigi"]
            )

            if (
                ema_farki
                >= yapilandirma.minimum_ema_farki_orani
                and kapanis_degeri > hizli_ema_degeri
                and hizli_ema_degeri > yavas_ema_degeri
                and egim > 0
            ):
                trend_rejimi = TREND_YUKSELIS

            elif (
                ema_farki
                >= yapilandirma.minimum_ema_farki_orani
                and kapanis_degeri < hizli_ema_degeri
                and hizli_ema_degeri < yavas_ema_degeri
                and egim < 0
            ):
                trend_rejimi = TREND_DUSUS

            else:
                trend_rejimi = TREND_YATAY

            volatilite_rejimi = (
                VOLATILITE_YUKSEK
                if atr_degeri
                > (
                    volatilite_esigi_degeri
                    * yapilandirma.yuksek_volatilite_carpani
                )
                else VOLATILITE_NORMAL
            )

            noktalar.append(
                MarketRegimePoint(
                    tarih=zaman.date(),
                    kapanis=kapanis_degeri,
                    hizli_ema=hizli_ema_degeri,
                    yavas_ema=yavas_ema_degeri,
                    atr_orani=atr_degeri,
                    volatilite_esigi_orani=(
                        volatilite_esigi_degeri
                    ),
                    trend_rejimi=trend_rejimi,
                    volatilite_rejimi=volatilite_rejimi,
                )
            )

        return tuple(noktalar)

    @staticmethod
    def _performans_olustur(
        rejim_adi: str,
        islemler: Iterable[BacktestTrade],
        toplam_islem_sayisi: int,
        backtest_yapilandirmasi: BacktestConfig,
    ) -> RegimePerformance:
        islem_tuple = tuple(islemler)
        metrikler = BacktestMetrics.hesapla(
            islemler=islem_tuple,
            yapilandirma=backtest_yapilandirmasi,
        )

        return RegimePerformance(
            rejim_adi=rejim_adi,
            islem_sayisi=metrikler.islem_sayisi,
            toplam_islem_orani=(
                metrikler.islem_sayisi / toplam_islem_sayisi
                if toplam_islem_sayisi > 0
                else 0.0
            ),
            kazanan_islem_sayisi=(
                metrikler.kazanan_islem_sayisi
            ),
            kaybeden_islem_sayisi=(
                metrikler.kaybeden_islem_sayisi
            ),
            basabas_islem_sayisi=(
                metrikler.basabas_islem_sayisi
            ),
            kazanma_orani=metrikler.kazanma_orani,
            ortalama_net_getiri_orani=(
                metrikler.ortalama_net_getiri_orani
            ),
            toplam_net_getiri_orani=(
                metrikler.toplam_net_getiri_orani
            ),
            kar_faktoru=metrikler.kar_faktoru,
            maksimum_ardisik_kayip=(
                metrikler.maksimum_ardisik_kayip
            ),
        )

    @staticmethod
    def _gun_dagilimini_olustur(
        gunluk_noktalar: tuple[MarketRegimePoint, ...],
        alan_adi: str,
        rejim_sirasi: tuple[str, ...],
    ) -> tuple[RegimeDayCount, ...]:
        sayac = Counter(
            getattr(nokta, alan_adi)
            for nokta in gunluk_noktalar
        )
        toplam_gun = len(gunluk_noktalar)

        return tuple(
            RegimeDayCount(
                rejim_adi=rejim,
                gun_sayisi=sayac.get(rejim, 0),
                toplam_gun_orani=(
                    sayac.get(rejim, 0) / toplam_gun
                    if toplam_gun > 0
                    else 0.0
                ),
            )
            for rejim in rejim_sirasi
        )
