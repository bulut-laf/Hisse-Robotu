from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from hashlib import sha256

import pandas as pd

from .analysis_profile import AnalysisProfile


class AnalysisContextError(ValueError):
    """Analiz veri bağlamı oluşturulamadığında kullanılan hata."""


@dataclass(frozen=True)
class AnalysisContext:
    """Bir raporun veri penceresi ve ortak ayar kimlikleri."""

    ilk_tarih: date
    son_tarih: date
    fiyat_bar_sayisi: int
    veri_kimligi: str
    ayar_kimligi: str

    @property
    def analiz_kimligi(self) -> str:
        icerik = (
            f"{self.veri_kimligi}|{self.ayar_kimligi}"
        ).encode("utf-8")
        return sha256(icerik).hexdigest()[:12]


def analiz_baglamini_olustur(
    fiyat_verisi: pd.DataFrame,
    profil: AnalysisProfile,
) -> AnalysisContext:
    veri = _fiyat_verisini_hazirla(fiyat_verisi)

    return AnalysisContext(
        ilk_tarih=veri.index[0].date(),
        son_tarih=veri.index[-1].date(),
        fiyat_bar_sayisi=len(veri),
        veri_kimligi=_veri_kimligini_hesapla(veri),
        ayar_kimligi=profil.ayar_kimligi,
    )


def _fiyat_verisini_hazirla(
    fiyat_verisi: pd.DataFrame,
) -> pd.DataFrame:
    if not isinstance(fiyat_verisi, pd.DataFrame):
        raise AnalysisContextError(
            "Fiyat verisi pandas DataFrame olmalıdır."
        )

    if fiyat_verisi.empty:
        raise AnalysisContextError("Fiyat verisi boş olamaz.")

    kopya = fiyat_verisi.copy()
    tarihler = pd.to_datetime(kopya.index, errors="coerce")

    if tarihler.isna().any():
        raise AnalysisContextError(
            "Fiyat verisinde geçersiz tarihler var."
        )

    kopya.index = tarihler
    kopya = kopya.sort_index()
    kopya = kopya.loc[~kopya.index.duplicated(keep="last")]

    kullanilan_sutunlar = [
        sutun
        for sutun in ("Open", "High", "Low", "Close", "Volume")
        if sutun in kopya.columns
    ]

    if not kullanilan_sutunlar:
        raise AnalysisContextError(
            "Fiyat verisinde kimlik üretilecek fiyat sütunu yok."
        )

    kopya = kopya[kullanilan_sutunlar]

    for sutun in kullanilan_sutunlar:
        kopya[sutun] = pd.to_numeric(
            kopya[sutun], errors="coerce"
        )

    if kopya.isna().any().any():
        raise AnalysisContextError(
            "Fiyat verisinde eksik veya sayısal olmayan değer var."
        )

    return kopya


def _veri_kimligini_hesapla(veri: pd.DataFrame) -> str:
    hash_degerleri = pd.util.hash_pandas_object(
        veri,
        index=True,
        categorize=False,
    )
    icerik = hash_degerleri.to_numpy().tobytes()
    return sha256(icerik).hexdigest()[:12]
