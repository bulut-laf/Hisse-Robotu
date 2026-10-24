from backend.app.prebreakout.prebreakout_engine import (
    on_yukselis_hazirligini_analiz_et,
)
from backend.app.prebreakout.prebreakout_models import PreBreakoutStage
from backend.tests.prebreakout_test_helpers import ornek_veri


def test_motor_deterministik_sonuc_uretir() -> None:
    data = ornek_veri()
    first = on_yukselis_hazirligini_analiz_et("TEST.IS", data)
    second = on_yukselis_hazirligini_analiz_et("TEST.IS", data)
    assert first == second


def test_yuksek_primli_hisse_erken_aday_olamaz() -> None:
    result = on_yukselis_hazirligini_analiz_et(
        "PRIM.IS",
        ornek_veri(son_gun_sicrama_pct=7.0),
    )
    assert result.late_entry is True
    assert result.accepted is False
    assert result.stage is PreBreakoutStage.HAREKET_BASLAMIS


def test_yetersiz_veri_reddedilir() -> None:
    result = on_yukselis_hazirligini_analiz_et(
        "AZ.IS",
        ornek_veri(gun=40),
    )
    assert result.accepted is False
    assert result.stage is PreBreakoutStage.REDDEDILDI


def test_sonuc_aciklama_ve_risk_listeleri_icerir() -> None:
    result = on_yukselis_hazirligini_analiz_et(
        "TEST.IS",
        ornek_veri(),
    )
    assert isinstance(result.reasons, tuple)
    assert isinstance(result.risks, tuple)
    assert result.component_scores is not None
