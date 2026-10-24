import pytest

from backend.app.analysis.momentum_discovery import MomentumDiscoveryRequest
from backend.app.analysis.trend_scan_policy import (
    REJIM_POZITIF,
    REJIM_RISKLI,
    REJIM_SECICI,
)


@pytest.mark.parametrize(
    "rejim",
    (REJIM_POZITIF, REJIM_SECICI, REJIM_RISKLI),
)
def test_request_gecerli_piyasa_rejimlerini_kabul_eder(rejim: str) -> None:
    istek = MomentumDiscoveryRequest(piyasa_rejimi=rejim)

    assert istek.piyasa_rejimi == rejim


def test_request_rejim_olmadan_geriye_uyumlu_calısir() -> None:
    istek = MomentumDiscoveryRequest()

    assert istek.piyasa_rejimi is None


def test_request_gecersiz_piyasa_rejimini_reddeder() -> None:
    with pytest.raises(ValueError, match="piyasa rejimi"):
        MomentumDiscoveryRequest(piyasa_rejimi="Bilinmeyen")


def test_result_rejim_alanlari_kaynakta_korunur() -> None:
    from pathlib import Path

    kaynak = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "analysis"
        / "momentum_discovery.py"
    ).read_text(encoding="utf-8")

    assert (
        "trend_politikasi_elenenler: tuple[MomentumCandidate, ...] = ()"
        in kaynak
    )
    assert "veri_tazeligi_kilidi_aktif: bool | None = None" in kaynak
    assert "veri_getirici is toplu_fiyat_verisi_getir" in kaynak
    assert "and veri_tazeligi.kilitli" in kaynak


def test_result_kurtarma_telemetri_alanlari_kaynakta_korunur() -> None:
    from pathlib import Path

    kaynak = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "analysis"
        / "momentum_discovery.py"
    ).read_text(encoding="utf-8")

    assert "yeniden_deneme_sayisi: int = 0" in kaynak
    assert "veri_kaynagi: str = " in kaynak
    assert "tazelik_kilit_asamasi: str = " in kaynak
    assert "sonraki_kontrol_zamani: str = " in kaynak
    assert "on_tazelik_azami_yeniden_deneme: int = 2" in kaynak
