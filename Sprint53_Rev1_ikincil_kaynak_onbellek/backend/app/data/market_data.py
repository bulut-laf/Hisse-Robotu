from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf


GEREKLI_SUTUNLAR = ["Open", "High", "Low", "Close", "Volume"]


class MarketDataError(Exception):
    """Piyasa verisi alınamadığında oluşturulan özel hata."""


def fiyat_verisi_getir(
    sembol: str,
    islem_gunu: int = 60,
    indirme_donemi: str = "6mo",
    yalnizca_tamamlanmis_gunler: bool = True,
) -> pd.DataFrame:
    """
    Belirtilen hisse için günlük fiyat ve hacim verisini indirir.

    Parametreler:
        sembol:
            Yahoo Finance hisse kodu.
            BIST örneği: THYAO.IS
            ABD örneği: AAPL

        islem_gunu:
            Sonuçta döndürülecek işlem günü sayısı.

        indirme_donemi:
            Göstergeleri hesaplamak için indirilecek toplam dönem.

        yalnizca_tamamlanmis_gunler:
            True olduğunda bugüne ait günlük mum analizden çıkarılır.
            Böylece gün içinde henüz tamamlanmamış fiyat ve hacim
            verileri sinyalleri bozmaz.

    Dönen değer:
        Open, High, Low, Close ve Volume sütunlarını içeren DataFrame.
    """
    temiz_sembol = sembol.strip().upper()

    if not temiz_sembol:
        raise ValueError("Hisse sembolü boş olamaz.")

    if islem_gunu < 1:
        raise ValueError("İşlem günü sayısı en az 1 olmalıdır.")

    try:
        veri = yf.download(
            tickers=temiz_sembol,
            period=indirme_donemi,
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=False,
            timeout=30,
        )
    except Exception as hata:
        raise MarketDataError(
            f"{temiz_sembol} verisi indirilirken hata oluştu: {hata}"
        ) from hata

    if veri is None or veri.empty:
        raise MarketDataError(
            f"{temiz_sembol} için piyasa verisi bulunamadı."
        )

    veri = fiyat_verisini_duzelt(
        veri,
        yalnizca_tamamlanmis_gunler=yalnizca_tamamlanmis_gunler,
    )

    if len(veri) < islem_gunu:
        raise MarketDataError(
            f"{temiz_sembol} için yalnızca {len(veri)} tamamlanmış "
            f"işlem günü bulundu. İstenen: {islem_gunu}"
        )

    return veri.tail(islem_gunu).copy()


def fiyat_verisini_duzelt(
    veri: pd.DataFrame,
    yalnizca_tamamlanmis_gunler: bool = True,
) -> pd.DataFrame:
    """
    Ham yfinance verisini Hisse Robotu'nun standart OHLCV biçimine dönüştürür.

    Tek sembol ve toplu indirme katmanları aynı normalizasyonu kullandığı için
    göstergeler bütün tarama yollarında aynı veri kurallarıyla hesaplanır.
    """
    if veri is None or veri.empty:
        raise MarketDataError("Piyasa verisi boş olamaz.")

    temiz_veri = _sutunlari_duzelt(veri)

    if yalnizca_tamamlanmis_gunler:
        temiz_veri = _bugunun_satirini_cikar(temiz_veri)

    return temiz_veri


def _bugunun_satirini_cikar(
    veri: pd.DataFrame,
) -> pd.DataFrame:
    """
    Günlük veri tablosunda bugüne ait satır varsa çıkarır.

    Gün içindeki günlük mum henüz tamamlanmamış olabileceği için
    günlük/swing analizlerde önceki tamamlanmış işlem günü kullanılır.
    """
    if veri.empty:
        return veri.copy()

    bugun = datetime.now(
        ZoneInfo("Europe/Istanbul")
    ).date()

    son_veri_tarihi = pd.Timestamp(
        veri.index[-1]
    ).date()

    if son_veri_tarihi == bugun:
        return veri.iloc[:-1].copy()

    return veri.copy()


def _sutunlari_duzelt(
    veri: pd.DataFrame,
) -> pd.DataFrame:
    """
    yfinance tarafından döndürülebilen çok seviyeli sütunları
    standart fiyat sütunlarına dönüştürür.
    """
    temiz_veri = veri.copy()

    if isinstance(temiz_veri.columns, pd.MultiIndex):
        temiz_veri.columns = (
            temiz_veri.columns.get_level_values(0)
        )

    eksik_sutunlar = [
        sutun
        for sutun in GEREKLI_SUTUNLAR
        if sutun not in temiz_veri.columns
    ]

    if eksik_sutunlar:
        raise MarketDataError(
            "Eksik piyasa verisi sütunları: "
            + ", ".join(eksik_sutunlar)
        )

    temiz_veri = temiz_veri[
        GEREKLI_SUTUNLAR
    ].copy()

    for sutun in GEREKLI_SUTUNLAR:
        temiz_veri[sutun] = pd.to_numeric(
            temiz_veri[sutun],
            errors="coerce",
        )

    temiz_veri = temiz_veri.dropna(
        subset=GEREKLI_SUTUNLAR
    )

    temiz_veri = _ohlc_araligini_duzelt(
        temiz_veri
    )

    temiz_veri.index = pd.to_datetime(
        temiz_veri.index
    )

    temiz_veri.index.name = "Date"

    return temiz_veri

def _ohlc_araligini_duzelt(
    veri: pd.DataFrame,
) -> pd.DataFrame:
    """
    Veri sağlayıcının günlük mumlarında görülebilen OHLC aralık
    tutarsızlıklarını güvenli biçimde normalleştirir.

    Bazı piyasa verilerinde açılış veya kapanış fiyatı, sağlayıcının
    bildirdiği gün içi en yüksek/en düşük aralığın çok az dışında
    kalabilir. Backtest motoru için günlük mumun tüm işlem fiyatlarını
    kapsaması gerektiğinden High en az Open/Close kadar yüksek, Low ise
    en fazla Open/Close kadar düşük olacak şekilde genişletilir.

    Open, Close ve Volume değerleri değiştirilmez.
    """
    sonuc = veri.copy()

    sonuc["High"] = sonuc[
        [
            "Open",
            "High",
            "Close",
        ]
    ].max(axis=1)

    sonuc["Low"] = sonuc[
        [
            "Open",
            "Low",
            "Close",
        ]
    ].min(axis=1)

    return sonuc



def guvenli_fiyat_verisi_getir(
    sembol: str,
    islem_gunu: int = 60,
    indirme_donemi: str = "6mo",
    *,
    ikincil_yukleyici=None,
    onbellek_klasoru=None,
):
    from pathlib import Path
    from .data_source_recovery import recover_daily_market_data

    recovered = recover_daily_market_data(
        sembol.strip().upper(),
        primary_loader=lambda: fiyat_verisi_getir(
            sembol,
            islem_gunu=islem_gunu,
            indirme_donemi=indirme_donemi,
            yalnizca_tamamlanmis_gunler=True,
        ),
        secondary_loader=ikincil_yukleyici,
        cache_root=Path(onbellek_klasoru) if onbellek_klasoru is not None else None,
    )
    if len(recovered.veri) < islem_gunu:
        raise MarketDataError(
            f"{sembol} için kurtarılan veri yalnızca {len(recovered.veri)} işlem günü içeriyor."
        )
    return recovered
