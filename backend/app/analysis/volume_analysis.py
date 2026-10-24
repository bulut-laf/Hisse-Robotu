from __future__ import annotations

import numpy as np
import pandas as pd


class VolumeAnalysisError(Exception):
    """Hacim analizi sırasında oluşan özel hata."""


def hacim_gostergelerini_ekle(
    veri: pd.DataFrame,
    ortalama_periyodu: int = 20,
    patlama_esigi: float = 1.50,
) -> pd.DataFrame:
    """
    Fiyat tablosuna hacim analizi göstergeleri ekler.

    Eklenen sütunlar:
        Ortalama_Hacim_20
        Hacim_Orani
        Gunluk_Getiri_Yuzde
        Hacim_Patlamasi
        Yukselis_Hacim_Patlamasi
        Dusus_Hacim_Patlamasi
        Fiyat_Hacim_Durumu

    Hacim patlaması:
        Güncel hacmin, önceki 20 işlem gününün ortalama
        hacminin en az 1,50 katına ulaşmasıdır.

    Önemli:
        Güncel günün hacmi, kendi karşılaştırma ortalamasına
        dahil edilmez. Bu nedenle rolling öncesinde shift(1)
        kullanılır.
    """
    gerekli_sutunlar = {
        "Close",
        "Volume",
    }

    eksik_sutunlar = gerekli_sutunlar.difference(
        veri.columns
    )

    if eksik_sutunlar:
        raise VolumeAnalysisError(
            "Hacim analizi için eksik sütunlar: "
            + ", ".join(sorted(eksik_sutunlar))
        )

    if ortalama_periyodu < 2:
        raise ValueError(
            "Hacim ortalama periyodu en az 2 olmalıdır."
        )

    if patlama_esigi <= 1:
        raise ValueError(
            "Hacim patlaması eşiği 1'den büyük olmalıdır."
        )

    sonuc = veri.copy()

    hacim_ortalama_sutunu = (
        f"Ortalama_Hacim_{ortalama_periyodu}"
    )

    sonuc[hacim_ortalama_sutunu] = (
        sonuc["Volume"]
        .shift(1)
        .rolling(
            window=ortalama_periyodu,
            min_periods=ortalama_periyodu,
        )
        .mean()
    )

    sonuc["Hacim_Orani"] = (
        sonuc["Volume"]
        / sonuc[hacim_ortalama_sutunu]
    )

    sonuc["Hacim_Orani"] = sonuc[
        "Hacim_Orani"
    ].replace(
        [np.inf, -np.inf],
        np.nan,
    )

    sonuc["Gunluk_Getiri_Yuzde"] = (
        sonuc["Close"]
        .pct_change()
        .mul(100)
    )

    sonuc["Hacim_Patlamasi"] = (
        sonuc["Hacim_Orani"] >= patlama_esigi
    )

    sonuc["Yukselis_Hacim_Patlamasi"] = (
        sonuc["Hacim_Patlamasi"]
        & (sonuc["Gunluk_Getiri_Yuzde"] > 0)
    )

    sonuc["Dusus_Hacim_Patlamasi"] = (
        sonuc["Hacim_Patlamasi"]
        & (sonuc["Gunluk_Getiri_Yuzde"] < 0)
    )

    sonuc["Fiyat_Hacim_Durumu"] = [
        _fiyat_hacim_durumu_belirle(
            gunluk_getiri=getiri,
            hacim_orani=hacim_orani,
            patlama_esigi=patlama_esigi,
        )
        for getiri, hacim_orani in zip(
            sonuc["Gunluk_Getiri_Yuzde"],
            sonuc["Hacim_Orani"],
            strict=True,
        )
    ]

    return sonuc


def _fiyat_hacim_durumu_belirle(
    gunluk_getiri: float,
    hacim_orani: float,
    patlama_esigi: float,
) -> str:
    """
    Tek bir işlem gününün fiyat-hacim ilişkisini sınıflandırır.
    """
    if pd.isna(gunluk_getiri) or pd.isna(hacim_orani):
        return "Yetersiz Veri"

    if hacim_orani >= patlama_esigi:
        if gunluk_getiri > 0:
            return "Yükseliş Hacim Onayı"

        if gunluk_getiri < 0:
            return "Düşüş Hacim Baskısı"

        return "Yüksek Hacim - Fiyat Değişmedi"

    if hacim_orani >= 1.00:
        if gunluk_getiri > 0:
            return "Normal Üzeri Hacimli Yükseliş"

        if gunluk_getiri < 0:
            return "Normal Üzeri Hacimli Düşüş"

        return "Normal Üzeri Hacim"

    return "Düşük/Normal Hacim"


def son_hacim_ozeti(
    veri: pd.DataFrame,
    ortalama_periyodu: int = 20,
) -> dict[str, object]:
    """
    Hacim göstergeleri eklenmiş tablonun son satırından
    sade bir analiz özeti üretir.
    """
    gerekli_sutunlar = {
        f"Ortalama_Hacim_{ortalama_periyodu}",
        "Volume",
        "Hacim_Orani",
        "Gunluk_Getiri_Yuzde",
        "Hacim_Patlamasi",
        "Yukselis_Hacim_Patlamasi",
        "Dusus_Hacim_Patlamasi",
        "Fiyat_Hacim_Durumu",
    }

    eksik_sutunlar = gerekli_sutunlar.difference(
        veri.columns
    )

    if eksik_sutunlar:
        raise VolumeAnalysisError(
            "Hacim özeti için eksik sütunlar: "
            + ", ".join(sorted(eksik_sutunlar))
        )

    if veri.empty:
        raise VolumeAnalysisError(
            "Hacim özeti üretilecek veri bulunamadı."
        )

    son = veri.iloc[-1]

    return {
        "hacim": int(son["Volume"]),
        "ortalama_hacim": (
            None
            if pd.isna(
                son[f"Ortalama_Hacim_{ortalama_periyodu}"]
            )
            else int(
                son[
                    f"Ortalama_Hacim_{ortalama_periyodu}"
                ]
            )
        ),
        "hacim_orani": (
            None
            if pd.isna(son["Hacim_Orani"])
            else round(
                float(son["Hacim_Orani"]),
                2,
            )
        ),
        "gunluk_getiri_yuzde": (
            None
            if pd.isna(son["Gunluk_Getiri_Yuzde"])
            else round(
                float(son["Gunluk_Getiri_Yuzde"]),
                2,
            )
        ),
        "hacim_patlamasi": bool(
            son["Hacim_Patlamasi"]
        ),
        "yukselis_hacim_patlamasi": bool(
            son["Yukselis_Hacim_Patlamasi"]
        ),
        "dusus_hacim_patlamasi": bool(
            son["Dusus_Hacim_Patlamasi"]
        ),
        "durum": str(
            son["Fiyat_Hacim_Durumu"]
        ),
    }