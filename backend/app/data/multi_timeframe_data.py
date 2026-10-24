from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from hashlib import sha256
from typing import Callable, Iterable
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

from .market_data import _sutunlari_duzelt


ISTANBUL = ZoneInfo("Europe/Istanbul")
SAATLIK = "Saatlik"
GUNLUK = "Günlük"
HAFTALIK = "Haftalık"
DESTEKLENEN_ARALIKLAR = ("1h", "1d", "1wk")


class MultiTimeframeDataError(Exception):
    """Çoklu zaman dilimi verisi hazırlanamadığında kullanılan hata."""


@dataclass(frozen=True)
class BistSessionConfig:
    """BIST tamamlanmış mum kontrolünde kullanılan temel seans bilgisi."""

    saat_dilimi: str = "Europe/Istanbul"
    seans_kapanisi: time = time(18, 10)
    kapanis_guvenlik_dakikasi: int = 10

    def __post_init__(self) -> None:
        if self.kapanis_guvenlik_dakikasi < 0:
            raise ValueError(
                "Kapanış güvenlik süresi negatif olamaz."
            )

        try:
            ZoneInfo(self.saat_dilimi)
        except Exception as hata:
            raise ValueError(
                f"Geçersiz saat dilimi: {self.saat_dilimi}"
            ) from hata

    @property
    def zaman_bolgesi(self) -> ZoneInfo:
        return ZoneInfo(self.saat_dilimi)


@dataclass(frozen=True)
class TimeframeConfig:
    """Bir zaman diliminin indirme ve minimum veri gereksinimleri."""

    ad: str
    interval: str
    period: str
    maksimum_bar: int
    minimum_bar: int = 60

    def __post_init__(self) -> None:
        temiz_ad = self.ad.strip()
        temiz_interval = self.interval.strip()
        temiz_period = self.period.strip()

        if not temiz_ad:
            raise ValueError("Zaman dilimi adı boş olamaz.")

        if temiz_interval not in DESTEKLENEN_ARALIKLAR:
            raise ValueError(
                "Desteklenmeyen zaman aralığı: "
                f"{temiz_interval}. Geçerli değerler: "
                + ", ".join(DESTEKLENEN_ARALIKLAR)
            )

        if not temiz_period:
            raise ValueError("İndirme dönemi boş olamaz.")

        if self.minimum_bar < 1:
            raise ValueError("Minimum bar sayısı en az 1 olmalıdır.")

        if self.maksimum_bar < self.minimum_bar:
            raise ValueError(
                "Maksimum bar sayısı minimum bardan küçük olamaz."
            )

        object.__setattr__(self, "ad", temiz_ad)
        object.__setattr__(self, "interval", temiz_interval)
        object.__setattr__(self, "period", temiz_period)


VARSAYILAN_ZAMAN_DILIMLERI = (
    TimeframeConfig(
        ad=SAATLIK,
        interval="1h",
        period="60d",
        maksimum_bar=300,
        minimum_bar=60,
    ),
    TimeframeConfig(
        ad=GUNLUK,
        interval="1d",
        period="2y",
        maksimum_bar=500,
        minimum_bar=60,
    ),
    TimeframeConfig(
        ad=HAFTALIK,
        interval="1wk",
        period="5y",
        maksimum_bar=260,
        minimum_bar=60,
    ),
)


@dataclass(frozen=True)
class TimeframeSnapshot:
    """Tek zaman dilimi için temizlenmiş ve tamamlanmış OHLCV verisi."""

    ad: str
    interval: str
    period: str
    veri: pd.DataFrame
    tamamlanmamis_bar_cikarildi: bool
    veri_kimligi: str

    @property
    def bar_sayisi(self) -> int:
        return len(self.veri)

    @property
    def ilk_zaman(self) -> pd.Timestamp:
        return pd.Timestamp(self.veri.index[0])

    @property
    def son_zaman(self) -> pd.Timestamp:
        return pd.Timestamp(self.veri.index[-1])


@dataclass(frozen=True)
class MultiTimeframeDataBundle:
    """Aynı BIST sembolünün saatlik, günlük ve haftalık veri paketi."""

    sembol: str
    zaman_dilimleri: tuple[TimeframeSnapshot, ...]
    veri_kimligi: str

    def getir(self, ad: str) -> TimeframeSnapshot:
        aranan = ad.strip().casefold()

        for zaman_dilimi in self.zaman_dilimleri:
            if zaman_dilimi.ad.casefold() == aranan:
                return zaman_dilimi

        raise KeyError(f"Zaman dilimi bulunamadı: {ad}")

    @property
    def ortak_referans_tarihi(self) -> pd.Timestamp:
        """Tüm zaman dilimlerinde tamamlanmış en ileri ortak tarihi döndürür."""
        return min(
            zaman_dilimi.son_zaman.normalize()
            for zaman_dilimi in self.zaman_dilimleri
        )


DataDownloader = Callable[..., pd.DataFrame]


def bist_sembolunu_hazirla(sembol: str) -> str:
    """BIST sembolünü Yahoo Finance biçimine dönüştürür."""
    temiz = sembol.strip().upper()

    if not temiz:
        raise ValueError("Hisse sembolü boş olamaz.")

    if not temiz.endswith(".IS"):
        temiz += ".IS"

    return temiz


def coklu_zaman_dilimi_verisi_getir(
    sembol: str,
    zaman_dilimleri: Iterable[TimeframeConfig] = VARSAYILAN_ZAMAN_DILIMLERI,
    veri_indirici: DataDownloader | None = None,
    simdi: datetime | None = None,
    seans: BistSessionConfig = BistSessionConfig(),
) -> MultiTimeframeDataBundle:
    """
    Bir BIST hissesi için saatlik, günlük ve haftalık veriyi hazırlar.

    Her zaman dilimi bağımsız indirilir, standart OHLCV biçimine çevrilir,
    tamamlanmamış son mum çıkarılır ve veri kimliği üretilir. Bu katman
    sinyal üretmez; sonraki çoklu zaman dilimi analizlerinin güvenli veri
    temelini sağlar.
    """
    temiz_sembol = bist_sembolunu_hazirla(sembol)
    ayarlar = tuple(zaman_dilimleri)
    _zaman_dilimlerini_dogrula(ayarlar)

    indirici = veri_indirici or yf.download
    analiz_zamani = _istanbul_zamani(simdi, seans)
    sonuclar: list[TimeframeSnapshot] = []

    for ayar in ayarlar:
        try:
            ham_veri = indirici(
                tickers=temiz_sembol,
                period=ayar.period,
                interval=ayar.interval,
                auto_adjust=True,
                progress=False,
                threads=False,
                timeout=30,
            )
        except Exception as hata:
            raise MultiTimeframeDataError(
                f"{temiz_sembol} {ayar.ad} verisi indirilirken "
                f"hata oluştu: {hata}"
            ) from hata

        if ham_veri is None or ham_veri.empty:
            raise MultiTimeframeDataError(
                f"{temiz_sembol} için {ayar.ad.lower()} veri bulunamadı."
            )

        veri = _zaman_indeksini_hazirla(
            _sutunlari_duzelt(ham_veri),
            seans,
        )
        veri, cikarildi = _tamamlanmamis_son_bari_cikar(
            veri=veri,
            interval=ayar.interval,
            simdi=analiz_zamani,
            seans=seans,
        )
        veri = veri.tail(ayar.maksimum_bar).copy()

        if len(veri) < ayar.minimum_bar:
            raise MultiTimeframeDataError(
                f"{temiz_sembol} {ayar.ad} verisinde yalnızca "
                f"{len(veri)} tamamlanmış bar var. "
                f"Gerekli minimum: {ayar.minimum_bar}"
            )

        sonuclar.append(
            TimeframeSnapshot(
                ad=ayar.ad,
                interval=ayar.interval,
                period=ayar.period,
                veri=veri,
                tamamlanmamis_bar_cikarildi=cikarildi,
                veri_kimligi=_veri_kimligi(
                    veri,
                    ayar.interval,
                ),
            )
        )

    paket_kimligi = _paket_kimligi(
        temiz_sembol,
        tuple(sonuclar),
    )

    return MultiTimeframeDataBundle(
        sembol=temiz_sembol,
        zaman_dilimleri=tuple(sonuclar),
        veri_kimligi=paket_kimligi,
    )


def _zaman_dilimlerini_dogrula(
    zaman_dilimleri: tuple[TimeframeConfig, ...],
) -> None:
    if not zaman_dilimleri:
        raise ValueError("En az bir zaman dilimi gereklidir.")

    adlar = [ayar.ad.casefold() for ayar in zaman_dilimleri]
    araliklar = [ayar.interval for ayar in zaman_dilimleri]

    if len(adlar) != len(set(adlar)):
        raise ValueError("Zaman dilimi adları benzersiz olmalıdır.")

    if len(araliklar) != len(set(araliklar)):
        raise ValueError("Zaman aralıkları benzersiz olmalıdır.")


def _istanbul_zamani(
    simdi: datetime | None,
    seans: BistSessionConfig,
) -> datetime:
    zaman_bolgesi = seans.zaman_bolgesi

    if simdi is None:
        return datetime.now(zaman_bolgesi)

    if simdi.tzinfo is None:
        return simdi.replace(tzinfo=zaman_bolgesi)

    return simdi.astimezone(zaman_bolgesi)


def _zaman_indeksini_hazirla(
    veri: pd.DataFrame,
    seans: BistSessionConfig,
) -> pd.DataFrame:
    sonuc = veri.copy()
    indeks = pd.DatetimeIndex(pd.to_datetime(sonuc.index, errors="coerce"))

    if indeks.isna().any():
        raise MultiTimeframeDataError(
            "Piyasa verisinde geçersiz zaman damgası bulundu."
        )

    if indeks.tz is not None:
        indeks = indeks.tz_convert(seans.zaman_bolgesi).tz_localize(None)

    sonuc.index = indeks
    sonuc = sonuc.sort_index()
    sonuc = sonuc.loc[~sonuc.index.duplicated(keep="last")]
    sonuc.index.name = "Date"

    return sonuc


def _tamamlanmamis_son_bari_cikar(
    veri: pd.DataFrame,
    interval: str,
    simdi: datetime,
    seans: BistSessionConfig,
) -> tuple[pd.DataFrame, bool]:
    if veri.empty:
        return veri.copy(), False

    son_zaman = pd.Timestamp(veri.index[-1]).to_pydatetime()
    son_zaman = son_zaman.replace(tzinfo=seans.zaman_bolgesi)
    tamamlanma_zamani = _bar_tamamlanma_zamani(
        son_zaman,
        interval,
        seans,
    )

    if simdi < tamamlanma_zamani:
        return veri.iloc[:-1].copy(), True

    return veri.copy(), False


def _bar_tamamlanma_zamani(
    bar_baslangici: datetime,
    interval: str,
    seans: BistSessionConfig,
) -> datetime:
    guvenlik = timedelta(minutes=seans.kapanis_guvenlik_dakikasi)

    if interval == "1h":
        saat_sonu = bar_baslangici + timedelta(hours=1)
        seans_sonu = datetime.combine(
            bar_baslangici.date(),
            seans.seans_kapanisi,
            tzinfo=seans.zaman_bolgesi,
        ) + guvenlik
        return min(saat_sonu, seans_sonu)

    if interval == "1d":
        return datetime.combine(
            bar_baslangici.date(),
            seans.seans_kapanisi,
            tzinfo=seans.zaman_bolgesi,
        ) + guvenlik

    if interval == "1wk":
        hafta_baslangici = (
            bar_baslangici.date()
            - timedelta(days=bar_baslangici.weekday())
        )
        cuma = hafta_baslangici + timedelta(days=4)
        return datetime.combine(
            cuma,
            seans.seans_kapanisi,
            tzinfo=seans.zaman_bolgesi,
        ) + guvenlik

    raise ValueError(f"Desteklenmeyen zaman aralığı: {interval}")


def _veri_kimligi(
    veri: pd.DataFrame,
    interval: str,
) -> str:
    hash_degerleri = pd.util.hash_pandas_object(
        veri,
        index=True,
        categorize=False,
    )
    icerik = (
        interval.encode("utf-8")
        + hash_degerleri.to_numpy().tobytes()
    )
    return sha256(icerik).hexdigest()[:12]


def _paket_kimligi(
    sembol: str,
    zaman_dilimleri: tuple[TimeframeSnapshot, ...],
) -> str:
    icerik = "|".join(
        [sembol]
        + [
            f"{zaman_dilimi.interval}:{zaman_dilimi.veri_kimligi}"
            for zaman_dilimi in zaman_dilimleri
        ]
    ).encode("utf-8")
    return sha256(icerik).hexdigest()[:12]
