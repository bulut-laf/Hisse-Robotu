from __future__ import annotations

import pytest

from backend.app.risk.risk_engine import RiskEngineError
from backend.app.risk.structural_risk import (
    yapisal_risk_plani_olustur,
)


def test_yapisal_risk_plani_dogru_hesaplanir() -> None:
    plan = yapisal_risk_plani_olustur(
        giris_fiyati=100.0,
        atr=4.0,
        hedef_fiyati=112.0,
        stop_atr_katsayisi=1.50,
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
    assert plan.risk_notu == "Orta Volatiliteli"
    assert plan.filtreyi_gecti is True


def test_iki_altindaki_yapisal_oran_elenecek() -> None:
    plan = yapisal_risk_plani_olustur(
        giris_fiyati=100.0,
        atr=4.0,
        hedef_fiyati=109.0,
        stop_atr_katsayisi=1.50,
        minimum_risk_odul=2.00,
    )

    assert plan.risk_odul_orani == pytest.approx(
        1.50,
        abs=1e-10,
    )
    assert plan.filtreyi_gecti is False


def test_hedef_giris_fiyatinin_uzerinde_olmalidir() -> None:
    with pytest.raises(
        RiskEngineError,
        match="giriş fiyatının üzerinde",
    ):
        yapisal_risk_plani_olustur(
            giris_fiyati=100.0,
            atr=4.0,
            hedef_fiyati=100.0,
        )


def test_gecersiz_yapisal_risk_girdileri_hata_verir() -> None:
    gecersiz_girdiler = [
        {
            "giris_fiyati": 0.0,
            "atr": 4.0,
            "hedef_fiyati": 110.0,
        },
        {
            "giris_fiyati": 100.0,
            "atr": 0.0,
            "hedef_fiyati": 110.0,
        },
        {
            "giris_fiyati": 100.0,
            "atr": 4.0,
            "hedef_fiyati": 0.0,
        },
        {
            "giris_fiyati": 100.0,
            "atr": 4.0,
            "hedef_fiyati": 110.0,
            "stop_atr_katsayisi": 0.0,
        },
        {
            "giris_fiyati": 100.0,
            "atr": 4.0,
            "hedef_fiyati": 110.0,
            "minimum_risk_odul": 0.0,
        },
    ]

    for girdiler in gecersiz_girdiler:
        with pytest.raises(ValueError):
            yapisal_risk_plani_olustur(
                **girdiler
            )


def test_yapisal_planda_negatif_stop_engellenir() -> None:
    with pytest.raises(
        RiskEngineError,
        match="stop-loss",
    ):
        yapisal_risk_plani_olustur(
            giris_fiyati=5.0,
            atr=4.0,
            hedef_fiyati=10.0,
            stop_atr_katsayisi=1.50,
        )