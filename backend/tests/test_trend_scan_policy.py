from dataclasses import dataclass

import pytest

from backend.app.analysis.trend_scan_policy import (
    REJIM_POZITIF,
    REJIM_RISKLI,
    REJIM_SECICI,
    rejime_gore_trend_politikasi,
    trend_adayini_degerlendir,
)


@dataclass(frozen=True)
class Aday:
    momentum_skoru: int
    trend_puani: int
    yirmi_gunluk_zirve_uzakligi: float
    kirilim: bool
    sinif: str


def test_rejim_politikalari_giderek_sikilastir() -> None:
    pozitif = rejime_gore_trend_politikasi(REJIM_POZITIF)
    secici = rejime_gore_trend_politikasi(REJIM_SECICI)
    riskli = rejime_gore_trend_politikasi(REJIM_RISKLI)

    assert pozitif.minimum_momentum_skoru < secici.minimum_momentum_skoru
    assert secici.minimum_momentum_skoru < riskli.minimum_momentum_skoru
    assert pozitif.minimum_trend_puani < secici.minimum_trend_puani
    assert secici.minimum_trend_puani < riskli.minimum_trend_puani
    assert pozitif.azami_direnc_uzakligi > secici.azami_direnc_uzakligi
    assert secici.azami_direnc_uzakligi > riskli.azami_direnc_uzakligi


def test_pozitif_rejim_normal_adayi_gecirir() -> None:
    aday = Aday(60, 9, 0.04, False, "E2 — Dirence Yaklaşıyor")
    karar = trend_adayini_degerlendir(
        aday,
        rejime_gore_trend_politikasi(REJIM_POZITIF),
    )

    assert karar.uygun is True
    assert karar.nedenler == ()


def test_secici_rejim_zayif_adayi_reddeder() -> None:
    aday = Aday(60, 9, 0.04, False, "E2 — Dirence Yaklaşıyor")
    karar = trend_adayini_degerlendir(
        aday,
        rejime_gore_trend_politikasi(REJIM_SECICI),
    )

    assert karar.uygun is False
    assert len(karar.nedenler) == 3


def test_riskli_rejim_kirilim_veya_yuksek_hazirlik_ister() -> None:
    aday = Aday(80, 13, 0.01, False, "E2 — Dirence Yaklaşıyor")
    karar = trend_adayini_degerlendir(
        aday,
        rejime_gore_trend_politikasi(REJIM_RISKLI),
    )

    assert karar.uygun is False
    assert "Riskli rejimde" in karar.nedenler[0]


def test_riskli_rejim_e3_adayini_gecirir() -> None:
    aday = Aday(80, 13, 0.01, False, "E3 — Kırılım Öncesi Erken Uyarı")
    karar = trend_adayini_degerlendir(
        aday,
        rejime_gore_trend_politikasi(REJIM_RISKLI),
    )

    assert karar.uygun is True


def test_gecersiz_rejim_reddedilir() -> None:
    with pytest.raises(ValueError, match="Desteklenmeyen piyasa rejimi"):
        rejime_gore_trend_politikasi("Belirsiz")
