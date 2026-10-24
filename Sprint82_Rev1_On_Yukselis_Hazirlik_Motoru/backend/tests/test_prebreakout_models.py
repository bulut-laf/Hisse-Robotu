from backend.app.prebreakout.prebreakout_models import (
    PreBreakoutConfig,
    PreBreakoutStage,
)


def test_varsayilan_konfigurasyon_guvenli_esiklerle_gelir() -> None:
    config = PreBreakoutConfig()
    assert config.minimum_bar == 60
    assert config.maksimum_son_gun_getirisi_pct == 4.0
    assert config.minimum_risk_odul == 1.5


def test_asama_degerleri_sabittir() -> None:
    assert PreBreakoutStage.E1.value == "E1"
    assert PreBreakoutStage.HAREKET_BASLAMIS.value == "HAREKET_BASLAMIS"
