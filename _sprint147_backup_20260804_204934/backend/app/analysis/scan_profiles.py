from __future__ import annotations

from dataclasses import dataclass

from .scan_filter import (
    NOTR_GORUNUM,
    POZITIF_GORUNUM,
    TUM_GORUNUMLER,
    ScanFilterCriteria,
)


@dataclass(frozen=True)
class ScanProfile:
    """Hazır tarama profilini temsil eder."""

    ad: str
    aciklama: str
    kriterler: ScanFilterCriteria


_PROFILLER: dict[str, ScanProfile] = {
    "gevsek": ScanProfile(
        ad="Gevşek",
        aciklama=(
            "Daha fazla hisse gösterir. "
            "Ön eleme ve genel piyasa taraması için uygundur."
        ),
        kriterler=ScanFilterCriteria(
            minimum_skor=20,
            minimum_hacim_orani=0.50,
            risk_odul_filtresi_gerekli=False,
            izin_verilen_gorunumler=TUM_GORUNUMLER,
        ),
    ),
    "dengeli": ScanProfile(
        ad="Dengeli",
        aciklama=(
            "Skor, hacim ve risk/ödül koşullarını "
            "birlikte uygular."
        ),
        kriterler=ScanFilterCriteria(
            minimum_skor=50,
            minimum_hacim_orani=1.00,
            risk_odul_filtresi_gerekli=True,
            izin_verilen_gorunumler=(
                POZITIF_GORUNUM,
                NOTR_GORUNUM,
            ),
        ),
    ),
    "siki": ScanProfile(
        ad="Sıkı",
        aciklama=(
            "Yalnızca güçlü, hacim destekli ve "
            "risk/ödül koşulunu geçen pozitif hisseleri gösterir."
        ),
        kriterler=ScanFilterCriteria(
            minimum_skor=70,
            minimum_hacim_orani=1.20,
            risk_odul_filtresi_gerekli=True,
            izin_verilen_gorunumler=(
                POZITIF_GORUNUM,
            ),
        ),
    ),
}


def profil_al(
    profil_adi: str,
) -> ScanProfile:
    """
    Profil adını temizleyerek ilgili hazır profili döndürür.
    """
    temiz_ad = profil_adi.strip().lower()

    try:
        return _PROFILLER[temiz_ad]

    except KeyError as hata:
        raise ValueError(
            f"Bilinmeyen tarama profili: {profil_adi}. "
            f"Geçerli profiller: {', '.join(profil_adlari())}"
        ) from hata


def profil_adlari() -> tuple[str, ...]:
    """Kullanılabilir profil anahtarlarını döndürür."""

    return tuple(_PROFILLER.keys())


def tum_profilleri_getir() -> tuple[ScanProfile, ...]:
    """Bütün hazır profilleri tanımlı sırayla döndürür."""

    return tuple(_PROFILLER.values())