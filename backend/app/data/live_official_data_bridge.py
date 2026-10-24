from __future__ import annotations

from typing import Any

import pandas as pd

from .bist_official_batch_bridge import (
    load_latest_official_daily,
    merge_official_daily_bar,
)


def _normalize_symbol(symbol: str) -> str:
    clean = symbol.strip().upper()
    return clean if clean.endswith(".IS") else f"{clean}.IS"


def resmi_gunluk_cercevesi_guncelle(
    symbol: str,
    historical: pd.DataFrame,
) -> pd.DataFrame:
    """
    Mevcut tarihsel günlük seriyi bozmaz; yalnızca en yeni tamamlanmış
    Borsa İstanbul resmî günlük barını aynı tarih üzerinde üstün olacak
    biçimde birleştirir.

    Resmî kaynak geçici olarak alınamazsa mevcut seri korunur. Böylece
    veri tazeliği katmanı eski veriyi kilitlemeye devam eder.
    """
    normalized = _normalize_symbol(symbol)
    try:
        result = load_latest_official_daily((normalized,))
        official = result.veriler.get(normalized)
        if official is None or official.empty:
            return historical
        return merge_official_daily_bar(historical, official)
    except Exception:
        return historical


def resmi_gunluk_paketi_guncelle(
    package: Any,
    symbol: str,
) -> Any:
    """
    Çoklu zaman dilimi paketindeki yalnızca Günlük snapshot'ı resmî
    tamamlanmış barla günceller. Haftalık/saatlik veri yapısı ve mevcut
    nesne sözleşmesi korunur.
    """
    if not hasattr(package, "getir"):
        return package

    try:
        daily_snapshot = package.getir("Günlük")
        daily_data = getattr(daily_snapshot, "veri")
    except Exception:
        return package

    merged = resmi_gunluk_cercevesi_guncelle(symbol, daily_data)
    if merged is daily_data:
        return package

    try:
        object.__setattr__(daily_snapshot, "veri", merged)
    except Exception:
        try:
            setattr(daily_snapshot, "veri", merged)
        except Exception:
            return package

    return package
