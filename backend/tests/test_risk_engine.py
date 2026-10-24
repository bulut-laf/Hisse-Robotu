from __future__ import annotations

import pytest

from backend.app.risk.risk_engine import (
    RiskEngineError,
    risk_plani_olustur,
    volatilite_notu_belirle,
)


def test_varsayilan_risk_plani_dogru_hesaplanir() -> None:
    plan = risk_plani_olustur(
        giris_fiyati=100.0,
        atr=4.0,
        stop_atr_katsayisi=1.50,
        hedef_atr_katsayisi=3.00,
        minimum_risk_odul=2.00,
    )

    assert plan.stop_loss == pytest.approx(
        94.0,
        abs=1e-10,
    )

    assert plan.hedef_fiyat == pytest.approx(
        112.0,
        abs=1e-10,
    )

    assert plan.risk_tutari == pytest.approx(
        6.0,
        abs=1e-10,
    )

    assert plan.odul_tutari == pytest.approx(
        12.0,
        abs=1e-10,
    )

    assert plan.risk_odul_orani == pytest.approx(
        2.0,
        abs=1e-10,
    )

    assert plan.atr_yuzde == pytest.approx(
        4.0,
        abs=1e-10,
    )

    assert plan.risk_notu == "Orta Volatiliteli"
    assert plan.filtreyi_gecti is True


def test_iki_altindaki_risk_odul_elenecek() -> None:
    plan = risk_plani_olustur(
        giris_fiyati=100.0,
        atr=4.0,
        stop_atr_katsayisi=1.50,
        hedef_atr_katsayisi=2.50,
        minimum_risk_odul=2.00,
    )

    assert plan.risk_odul_orani == pytest.approx(
        2.50 / 1.50,
        abs=1e-10,
    )

    assert plan.risk_odul_orani < 2.0
    assert plan.filtreyi_gecti is False


def test_dusuk_volatilite_notu() -> None:
    assert (
        volatilite_notu_belirle(1.99)
        == "Düşük Volatiliteli"
    )


def test_orta_volatilite_sinirlari() -> None:
    assert (
        volatilite_notu_belirle(2.00)
        == "Orta Volatiliteli"
    )

    assert (
        volatilite_notu_belirle(4.00)
        == "Orta Volatiliteli"
    )


def test_yuksek_volatilite_notu() -> None:
    assert (
        volatilite_notu_belirle(4.01)
        == "Yüksek Volatiliteli"
    )


def test_gecersiz_girdiler_hata_verir() -> None:
    gecersiz_girdiler = [
        {
            "giris_fiyati": 0.0,
            "atr": 2.0,
        },
        {
            "giris_fiyati": 100.0,
            "atr": 0.0,
        },
        {
            "giris_fiyati": 100.0,
            "atr": 2.0,
            "stop_atr_katsayisi": 0.0,
        },
        {
            "giris_fiyati": 100.0,
            "atr": 2.0,
            "hedef_atr_katsayisi": 0.0,
        },
        {
            "giris_fiyati": 100.0,
            "atr": 2.0,
            "minimum_risk_odul": 0.0,
        },
    ]

    for girdiler in gecersiz_girdiler:
        with pytest.raises(ValueError):
            risk_plani_olustur(**girdiler)


def test_negatif_stop_loss_engellenir() -> None:
    with pytest.raises(RiskEngineError, match="stop-loss"):
        risk_plani_olustur(
            giris_fiyati=5.0,
            atr=4.0,
            stop_atr_katsayisi=1.50,
            hedef_atr_katsayisi=3.00,
        )


def test_sinir_degerindeki_kayan_nokta_farki_filtreyi_bozmaz() -> None:
    plan = risk_plani_olustur(
        giris_fiyati=370.0,
        atr=16.5123456789,
        stop_atr_katsayisi=1.50,
        hedef_atr_katsayisi=3.00,
        minimum_risk_odul=2.00,
    )

    assert plan.risk_odul_orani == pytest.approx(
        2.0,
        abs=1e-9,
    )
    assert plan.filtreyi_gecti is True