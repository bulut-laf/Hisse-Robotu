from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable
from zoneinfo import ZoneInfo

import pandas as pd


class CurrentSessionSnapshotError(Exception):
    """Güncel seans özeti alınamadığında kullanılır."""


@dataclass(frozen=True)
class CurrentSessionSnapshot:
    """Tarihsel sinyalden bağımsız, yalnızca bilgi amaçlı seans özeti."""

    sembol: str
    seans_tarihi: str
    son_veri_zamani: str
    acilis: float
    en_yuksek: float
    en_dusuk: float
    son_fiyat: float
    hacim: float
    bugunku_seans: bool

    def son_getiri(self, sinyal_fiyati: float) -> float | None:
        if sinyal_fiyati <= 0:
            return None
        return self.son_fiyat / sinyal_fiyati - 1.0

    def azami_getiri(self, sinyal_fiyati: float) -> float | None:
        if sinyal_fiyati <= 0:
            return None
        return self.en_yuksek / sinyal_fiyati - 1.0

    def azami_ters_hareket(self, sinyal_fiyati: float) -> float | None:
        if sinyal_fiyati <= 0:
            return None
        return max(0.0, 1.0 - self.en_dusuk / sinyal_fiyati)


Downloader = Callable[..., pd.DataFrame]


def guncel_seans_ozeti_getir(
    sembol: str,
    *,
    indirici: Downloader | None = None,
    simdi: datetime | None = None,
) -> CurrentSessionSnapshot:
    """
    Son erişilebilir seansı 5 dakikalık veriden özetler.

    Bu veri tarihsel aday üretiminde veya walk-forward ölçümünde kullanılmaz.
    Yalnızca kullanıcının tamamlanmış günlük barlarla güncel seans arasındaki
    farkı görmesi için ayrı bir bilgi kartı üretir.
    """
    temiz_sembol = sembol.strip().upper()
    if not temiz_sembol:
        raise ValueError("Hisse sembolü boş olamaz.")

    if indirici is None:
        try:
            import yfinance as yf
        except ImportError as hata:
            raise CurrentSessionSnapshotError(
                "Güncel seans verisi için yfinance paketi bulunamadı."
            ) from hata
        indirici = yf.download

    try:
        veri = indirici(
            tickers=temiz_sembol,
            period="5d",
            interval="5m",
            auto_adjust=True,
            progress=False,
            threads=False,
            prepost=False,
            timeout=30,
        )
    except Exception as hata:
        raise CurrentSessionSnapshotError(
            f"{temiz_sembol} güncel seans verisi alınamadı: {hata}"
        ) from hata

    if veri is None or veri.empty:
        raise CurrentSessionSnapshotError(
            f"{temiz_sembol} için güncel seans verisi bulunamadı."
        )

    temiz = _sutunlari_duzelt(veri)
    if temiz.empty:
        raise CurrentSessionSnapshotError(
            f"{temiz_sembol} güncel seans verisi kullanılabilir fiyat içermiyor."
        )

    istanbul = ZoneInfo("Europe/Istanbul")
    zamanlar = _istanbul_zamanlari(temiz.index, istanbul)
    son_tarih = zamanlar[-1].date()
    mask = [zaman.date() == son_tarih for zaman in zamanlar]
    seans = temiz.loc[mask].copy()
    seans_zamanlari = [zaman for zaman, dahil in zip(zamanlar, mask) if dahil]

    if seans.empty:
        raise CurrentSessionSnapshotError(
            f"{temiz_sembol} için son seans ayrıştırılamadı."
        )

    simdi_istanbul = simdi or datetime.now(istanbul)
    if simdi_istanbul.tzinfo is None:
        simdi_istanbul = simdi_istanbul.replace(tzinfo=istanbul)
    else:
        simdi_istanbul = simdi_istanbul.astimezone(istanbul)

    acilis = float(seans["Open"].iloc[0])
    en_yuksek = float(seans["High"].max())
    en_dusuk = float(seans["Low"].min())
    son_fiyat = float(seans["Close"].iloc[-1])
    hacim = float(seans["Volume"].sum())
    son_zaman = seans_zamanlari[-1]

    return CurrentSessionSnapshot(
        sembol=temiz_sembol,
        seans_tarihi=son_tarih.isoformat(),
        son_veri_zamani=son_zaman.strftime("%Y-%m-%d %H:%M"),
        acilis=acilis,
        en_yuksek=en_yuksek,
        en_dusuk=en_dusuk,
        son_fiyat=son_fiyat,
        hacim=hacim,
        bugunku_seans=son_tarih == simdi_istanbul.date(),
    )


def _sutunlari_duzelt(veri: pd.DataFrame) -> pd.DataFrame:
    sonuc = veri.copy()
    if isinstance(sonuc.columns, pd.MultiIndex):
        sonuc.columns = sonuc.columns.get_level_values(0)

    gerekli = ("Open", "High", "Low", "Close", "Volume")
    eksik = [sutun for sutun in gerekli if sutun not in sonuc.columns]
    if eksik:
        raise CurrentSessionSnapshotError(
            "Güncel seans verisinde eksik sütunlar: " + ", ".join(eksik)
        )

    sonuc = sonuc[list(gerekli)].copy()
    for sutun in gerekli:
        sonuc[sutun] = pd.to_numeric(sonuc[sutun], errors="coerce")
    sonuc = sonuc.dropna(subset=list(gerekli))
    return sonuc.sort_index()


def _istanbul_zamanlari(
    index: pd.Index,
    istanbul: ZoneInfo,
) -> list[pd.Timestamp]:
    zamanlar: list[pd.Timestamp] = []
    for deger in pd.to_datetime(index):
        zaman = pd.Timestamp(deger)
        if zaman.tzinfo is None:
            zaman = zaman.tz_localize(istanbul)
        else:
            zaman = zaman.tz_convert(istanbul)
        zamanlar.append(zaman)
    return zamanlar
