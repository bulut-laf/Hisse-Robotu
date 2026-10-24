from dataclasses import replace

from backend.app.analysis.momentum_discovery import (
    MomentumCandidate,
    MomentumDiscoveryRequest,
    SINIF_DIRENCE_YAKLASIYOR,
    SINIF_ERKEN_UYARI,
)
from backend.app.analysis.trend_scan_policy import (
    REJIM_POZITIF,
    REJIM_RISKLI,
    rejime_gore_trend_politikasi,
    trend_adayini_degerlendir,
)


def _aday(
    *,
    momentum: int = 80,
    trend: int = 13,
    uzaklik: float = 0.01,
    kirilim: bool = False,
    sinif: str = SINIF_ERKEN_UYARI,
) -> MomentumCandidate:
    return MomentumCandidate(
        sembol="AAA.IS",
        analiz_tarihi="2026-07-30",
        kapanis=100.0,
        momentum_skoru=momentum,
        sinif=sinif,
        goreceli_guc_puani=15,
        fiyat_ivmesi_puani=10,
        hacim_birikimi_puani=10,
        kirilim_hazirligi_puani=10,
        trend_puani=trend,
        likidite_puani=8,
        risk_kalitesi_puani=8,
        getiri_5g=0.03,
        getiri_20g=0.08,
        getiri_60g=0.15,
        hacim_orani=1.2,
        yirmi_gunluk_zirve_uzakligi=uzaklik,
        ortalama_tl_hacim=100_000_000.0,
        rsi14=60.0,
        atr_yuzde=2.5,
        teknik_skor=70,
        teknik_gorunum="Pozitif",
        risk_odul_orani=2.0,
        risk_odul_uygun=True,
        kirilim=kirilim,
        sikisma=False,
        asiri_uzamis=False,
        pozitif_nedenler=(),
        riskler=(),
    )


def test_request_piyasa_rejimini_kabul_eder() -> None:
    istek = MomentumDiscoveryRequest(piyasa_rejimi=REJIM_POZITIF)
    assert istek.piyasa_rejimi == REJIM_POZITIF


def test_request_gecersiz_piyasa_rejimini_reddeder() -> None:
    try:
        MomentumDiscoveryRequest(piyasa_rejimi="Belirsiz")
    except ValueError as hata:
        assert "Desteklenmeyen piyasa rejimi" in str(hata)
    else:
        raise AssertionError("Geçersiz piyasa rejimi reddedilmedi.")


def test_riskli_rejim_e3_adayini_gecirir() -> None:
    aday = _aday()
    karar = trend_adayini_degerlendir(
        aday,
        rejime_gore_trend_politikasi(REJIM_RISKLI),
    )
    assert karar.uygun is True


def test_riskli_rejim_e2_adayini_nedeniyle_reddeder() -> None:
    aday = replace(
        _aday(),
        sinif=SINIF_DIRENCE_YAKLASIYOR,
        kirilim=False,
    )
    karar = trend_adayini_degerlendir(
        aday,
        rejime_gore_trend_politikasi(REJIM_RISKLI),
    )
    assert karar.uygun is False
    assert any("Riskli rejimde" in neden for neden in karar.nedenler)


def test_pozitif_rejim_daha_esnek_adayi_gecirir() -> None:
    aday = _aday(
        momentum=58,
        trend=8,
        uzaklik=0.05,
        sinif=SINIF_DIRENCE_YAKLASIYOR,
    )
    karar = trend_adayini_degerlendir(
        aday,
        rejime_gore_trend_politikasi(REJIM_POZITIF),
    )
    assert karar.uygun is True
