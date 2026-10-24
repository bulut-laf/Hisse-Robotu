from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


class SupportResistanceError(Exception):
    """Destek ve direnç analizi sırasında oluşan özel hata."""


@dataclass(frozen=True)
class PriceLevel:
    """Bir destek veya direnç fiyat seviyesini temsil eder."""

    fiyat: float
    temas_sayisi: int
    guc: str
    son_temas_tarihi: str


@dataclass(frozen=True)
class SupportResistanceResult:
    """En yakın destek ve direnç analiz sonucu."""

    mevcut_fiyat: float

    destek: PriceLevel | None
    direnc: PriceLevel | None

    destek_uzaklik_yuzde: float | None
    direnc_uzaklik_yuzde: float | None

    pivot_dip_sayisi: int
    pivot_tepe_sayisi: int


@dataclass
class _LevelCluster:
    """Birbirine yakın fiyat seviyelerinin iç kümesi."""

    fiyatlar: list[float]
    tarihler: list[Any]

    @property
    def ortalama_fiyat(self) -> float:
        return sum(self.fiyatlar) / len(self.fiyatlar)

    @property
    def temas_sayisi(self) -> int:
        return len(self.fiyatlar)

    @property
    def son_temas_tarihi(self) -> Any:
        return max(self.tarihler)


def destek_direnc_bul(
    veri: pd.DataFrame,
    bakis_periyodu: int = 120,
    pivot_genisligi: int = 2,
    birlestirme_toleransi_yuzde: float = 1.00,
) -> SupportResistanceResult:
    """
    Yerel fiyat dipleri ve tepelerinden en yakın destek ve
    direnç seviyelerini belirler.

    pivot_genisligi=2 olduğunda bir fiyat seviyesi:

        Önceki 2 gün
        + ilgili gün
        + sonraki 2 gün

    ile karşılaştırılarak teyit edilir.
    """
    gerekli_sutunlar = {
        "High",
        "Low",
        "Close",
    }

    eksik_sutunlar = gerekli_sutunlar.difference(
        veri.columns
    )

    if eksik_sutunlar:
        raise SupportResistanceError(
            "Destek/direnç analizi için eksik sütunlar: "
            + ", ".join(sorted(eksik_sutunlar))
        )

    if bakis_periyodu <= 0:
        raise ValueError(
            "Bakış periyodu pozitif olmalıdır."
        )

    if pivot_genisligi <= 0:
        raise ValueError(
            "Pivot genişliği pozitif olmalıdır."
        )

    if birlestirme_toleransi_yuzde <= 0:
        raise ValueError(
            "Birleştirme toleransı pozitif olmalıdır."
        )

    minimum_satir = (pivot_genisligi * 2) + 3

    temiz_veri = (
        veri[["High", "Low", "Close"]]
        .dropna()
        .sort_index()
        .tail(bakis_periyodu)
        .copy()
    )

    if len(temiz_veri) < minimum_satir:
        raise SupportResistanceError(
            "Destek ve direnç analizi için yeterli veri yok. "
            f"En az {minimum_satir} satır gereklidir."
        )

    mevcut_fiyat = float(
        temiz_veri["Close"].iloc[-1]
    )

    if mevcut_fiyat <= 0:
        raise SupportResistanceError(
            "Mevcut kapanış fiyatı pozitif olmalıdır."
        )

    pencere = (pivot_genisligi * 2) + 1

    yuvarlanan_dip = (
        temiz_veri["Low"]
        .rolling(
            window=pencere,
            center=True,
        )
        .min()
    )

    yuvarlanan_tepe = (
        temiz_veri["High"]
        .rolling(
            window=pencere,
            center=True,
        )
        .max()
    )

    pivot_dip_maskesi = (
        temiz_veri["Low"] == yuvarlanan_dip
    )

    pivot_tepe_maskesi = (
        temiz_veri["High"] == yuvarlanan_tepe
    )

    pivot_dipler = [
        (
            float(temiz_veri.at[tarih, "Low"]),
            tarih,
        )
        for tarih in temiz_veri.index[pivot_dip_maskesi]
    ]

    pivot_tepeler = [
        (
            float(temiz_veri.at[tarih, "High"]),
            tarih,
        )
        for tarih in temiz_veri.index[pivot_tepe_maskesi]
    ]

    destek_kumeleri = _seviyeleri_birlestir(
        seviyeler=pivot_dipler,
        tolerans_yuzde=birlestirme_toleransi_yuzde,
    )

    direnc_kumeleri = _seviyeleri_birlestir(
        seviyeler=pivot_tepeler,
        tolerans_yuzde=birlestirme_toleransi_yuzde,
    )

    destek_adaylari = [
        kume
        for kume in destek_kumeleri
        if kume.ortalama_fiyat < mevcut_fiyat
    ]

    direnc_adaylari = [
        kume
        for kume in direnc_kumeleri
        if kume.ortalama_fiyat > mevcut_fiyat
    ]

    en_yakin_destek_kumesi = (
        max(
            destek_adaylari,
            key=lambda kume: kume.ortalama_fiyat,
        )
        if destek_adaylari
        else None
    )

    en_yakin_direnc_kumesi = (
        min(
            direnc_adaylari,
            key=lambda kume: kume.ortalama_fiyat,
        )
        if direnc_adaylari
        else None
    )

    destek = _fiyat_seviyesi_olustur(
        en_yakin_destek_kumesi
    )

    direnc = _fiyat_seviyesi_olustur(
        en_yakin_direnc_kumesi
    )

    destek_uzaklik_yuzde = (
        (
            (mevcut_fiyat - destek.fiyat)
            / mevcut_fiyat
        )
        * 100
        if destek is not None
        else None
    )

    direnc_uzaklik_yuzde = (
        (
            (direnc.fiyat - mevcut_fiyat)
            / mevcut_fiyat
        )
        * 100
        if direnc is not None
        else None
    )

    return SupportResistanceResult(
        mevcut_fiyat=mevcut_fiyat,
        destek=destek,
        direnc=direnc,
        destek_uzaklik_yuzde=destek_uzaklik_yuzde,
        direnc_uzaklik_yuzde=direnc_uzaklik_yuzde,
        pivot_dip_sayisi=len(pivot_dipler),
        pivot_tepe_sayisi=len(pivot_tepeler),
    )


def _seviyeleri_birlestir(
    seviyeler: list[tuple[float, Any]],
    tolerans_yuzde: float,
) -> list[_LevelCluster]:
    """
    Birbirine yakın fiyat seviyelerini tek kümede birleştirir.
    """
    if not seviyeler:
        return []

    sirali_seviyeler = sorted(
        seviyeler,
        key=lambda seviye: seviye[0],
    )

    kumeler: list[_LevelCluster] = []

    for fiyat, tarih in sirali_seviyeler:
        if fiyat <= 0:
            continue

        if not kumeler:
            kumeler.append(
                _LevelCluster(
                    fiyatlar=[fiyat],
                    tarihler=[tarih],
                )
            )
            continue

        son_kume = kumeler[-1]
        ortalama_fiyat = son_kume.ortalama_fiyat

        fark_yuzde = (
            abs(fiyat - ortalama_fiyat)
            / ortalama_fiyat
        ) * 100

        if fark_yuzde <= tolerans_yuzde:
            son_kume.fiyatlar.append(fiyat)
            son_kume.tarihler.append(tarih)
        else:
            kumeler.append(
                _LevelCluster(
                    fiyatlar=[fiyat],
                    tarihler=[tarih],
                )
            )

    return kumeler


def _fiyat_seviyesi_olustur(
    kume: _LevelCluster | None,
) -> PriceLevel | None:
    if kume is None:
        return None

    return PriceLevel(
        fiyat=float(kume.ortalama_fiyat),
        temas_sayisi=kume.temas_sayisi,
        guc=_seviye_gucu_belirle(
            kume.temas_sayisi
        ),
        son_temas_tarihi=_tarih_metnine_donustur(
            kume.son_temas_tarihi
        ),
    )


def _seviye_gucu_belirle(
    temas_sayisi: int,
) -> str:
    if temas_sayisi >= 3:
        return "Güçlü"

    if temas_sayisi == 2:
        return "Orta"

    return "Zayıf"


def _tarih_metnine_donustur(
    tarih: Any,
) -> str:
    if hasattr(tarih, "date"):
        return str(tarih.date())

    return str(tarih)