from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from backend.app.analysis.scan_filter import (
    NEGATIF_GORUNUM,
    NOTR_GORUNUM,
    POZITIF_GORUNUM,
    ScanFilterCriteria,
    tarama_sonucunu_filtrele,
)
from backend.app.analysis.stock_scanner import (
    ScanFailure,
    StockScanResult,
)


def ornek_sonuc(
    sembol: str,
    skor: int,
    karar: str,
    hacim_orani: float,
    filtreyi_gecti: bool,
) -> Any:
    return SimpleNamespace(
        sembol=sembol,
        hacim_orani=hacim_orani,
        sinyal=SimpleNamespace(
            skor=skor,
            karar=karar,
        ),
        risk_plani=SimpleNamespace(
            filtreyi_gecti=filtreyi_gecti,
        ),
    )


def ornek_tarama() -> StockScanResult:
    return StockScanResult(
        basarili_sonuclar=(
            ornek_sonuc(
                sembol="AAA.IS",
                skor=80,
                karar=POZITIF_GORUNUM,
                hacim_orani=1.60,
                filtreyi_gecti=True,
            ),
            ornek_sonuc(
                sembol="BBB.IS",
                skor=55,
                karar=NOTR_GORUNUM,
                hacim_orani=1.10,
                filtreyi_gecti=True,
            ),
            ornek_sonuc(
                sembol="CCC.IS",
                skor=30,
                karar=NEGATIF_GORUNUM,
                hacim_orani=0.70,
                filtreyi_gecti=False,
            ),
        ),
        hatalar=(
            ScanFailure(
                sembol="HATALI.IS",
                hata="Veri bulunamadı.",
            ),
        ),
    )


def test_varsayilan_filtre_tum_sonuclari_kabul_eder() -> None:
    sonuc = tarama_sonucunu_filtrele(
        tarama=ornek_tarama(),
        kriterler=ScanFilterCriteria(),
    )

    assert [
        aday.sembol
        for aday in sonuc.adaylar
    ] == [
        "AAA.IS",
        "BBB.IS",
        "CCC.IS",
    ]

    assert sonuc.aday_sayisi == 3
    assert sonuc.elenen_sayisi == 0
    assert sonuc.hatali_sayisi == 1
    assert sonuc.toplam_sayisi == 4


def test_minimum_skor_filtresi_uygulanir() -> None:
    sonuc = tarama_sonucunu_filtrele(
        tarama=ornek_tarama(),
        kriterler=ScanFilterCriteria(
            minimum_skor=60,
        ),
    )

    assert [
        aday.sembol
        for aday in sonuc.adaylar
    ] == [
        "AAA.IS",
    ]

    assert [
        elenen.sembol
        for elenen in sonuc.elenenler
    ] == [
        "BBB.IS",
        "CCC.IS",
    ]


def test_hacim_filtresi_uygulanir() -> None:
    sonuc = tarama_sonucunu_filtrele(
        tarama=ornek_tarama(),
        kriterler=ScanFilterCriteria(
            minimum_hacim_orani=1.20,
        ),
    )

    assert [
        aday.sembol
        for aday in sonuc.adaylar
    ] == [
        "AAA.IS",
    ]

    assert "Hacim oranı" in (
        sonuc.elenenler[0].nedenler[0]
    )


def test_risk_odul_filtresi_uygulanir() -> None:
    sonuc = tarama_sonucunu_filtrele(
        tarama=ornek_tarama(),
        kriterler=ScanFilterCriteria(
            risk_odul_filtresi_gerekli=True,
        ),
    )

    assert [
        aday.sembol
        for aday in sonuc.adaylar
    ] == [
        "AAA.IS",
        "BBB.IS",
    ]

    assert sonuc.elenenler[0].sembol == "CCC.IS"
    assert (
        "Risk/ödül filtresini geçemedi."
        in sonuc.elenenler[0].nedenler
    )


def test_gorunum_filtresi_uygulanir() -> None:
    sonuc = tarama_sonucunu_filtrele(
        tarama=ornek_tarama(),
        kriterler=ScanFilterCriteria(
            izin_verilen_gorunumler=(
                POZITIF_GORUNUM,
                NOTR_GORUNUM,
            ),
        ),
    )

    assert [
        aday.sembol
        for aday in sonuc.adaylar
    ] == [
        "AAA.IS",
        "BBB.IS",
    ]

    assert sonuc.elenenler[0].sembol == "CCC.IS"


def test_bir_hisse_birden_fazla_nedenle_elenebilir() -> None:
    sonuc = tarama_sonucunu_filtrele(
        tarama=ornek_tarama(),
        kriterler=ScanFilterCriteria(
            minimum_skor=60,
            minimum_hacim_orani=1.20,
            risk_odul_filtresi_gerekli=True,
            izin_verilen_gorunumler=(
                POZITIF_GORUNUM,
            ),
        ),
    )

    ccc = next(
        elenen
        for elenen in sonuc.elenenler
        if elenen.sembol == "CCC.IS"
    )

    assert len(ccc.nedenler) == 4

def test_gecersiz_filtre_kriterleri_hata_verir() -> None:
    gecersiz_kriterler = [
        {
            "minimum_skor": -1,
        },
        {
            "minimum_skor": 101,
        },
        {
            "minimum_hacim_orani": -0.01,
        },
        {
            "izin_verilen_gorunumler": (),
        },
        {
            "izin_verilen_gorunumler": (
                "Bilinmeyen Görünüm",
            ),
        },
    ]

    for kriterler in gecersiz_kriterler:
        with pytest.raises(ValueError):
            ScanFilterCriteria(**kriterler)


def test_elenen_hissenin_analiz_sonucu_korunur() -> None:
    sonuc = tarama_sonucunu_filtrele(
        tarama=ornek_tarama(),
        kriterler=ScanFilterCriteria(
            minimum_skor=60,
        ),
    )

    ccc = next(
        elenen
        for elenen in sonuc.elenenler
        if elenen.sembol == "CCC.IS"
    )

    assert ccc.sonuc is not None
    assert ccc.sonuc.sembol == "CCC.IS"
    assert ccc.sonuc.sinyal.skor == 30
    assert ccc.sonuc.hacim_orani == pytest.approx(
        0.70,
        abs=1e-10,
    )
