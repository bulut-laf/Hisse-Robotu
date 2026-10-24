from __future__ import annotations

from backend.app.analysis.scan_filter import (
    NOTR_GORUNUM,
    POZITIF_GORUNUM,
    TUM_GORUNUMLER,
)
from backend.app.analysis.scan_profiles import profil_al


def test_sprint147_dengeli_aday_kesfi_rr_hard_filter_kullanmaz() -> None:
    profil = profil_al("dengeli")

    assert profil.kriterler.minimum_skor == 50
    assert profil.kriterler.minimum_hacim_orani == 1.00
    assert profil.kriterler.risk_odul_filtresi_gerekli is False
    assert profil.kriterler.izin_verilen_gorunumler == (
        POZITIF_GORUNUM,
        NOTR_GORUNUM,
    )


def test_sprint147_gevsek_ve_siki_profiller_degismez() -> None:
    gevsek = profil_al("gevsek")
    siki = profil_al("siki")

    assert gevsek.kriterler.minimum_skor == 20
    assert gevsek.kriterler.minimum_hacim_orani == 0.50
    assert gevsek.kriterler.risk_odul_filtresi_gerekli is False
    assert gevsek.kriterler.izin_verilen_gorunumler == TUM_GORUNUMLER

    assert siki.kriterler.minimum_skor == 70
    assert siki.kriterler.minimum_hacim_orani == 1.20
    assert siki.kriterler.risk_odul_filtresi_gerekli is True
    assert siki.kriterler.izin_verilen_gorunumler == (POZITIF_GORUNUM,)
