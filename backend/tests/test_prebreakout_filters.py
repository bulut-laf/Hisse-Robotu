from backend.app.prebreakout.prebreakout_features import ozellikleri_hesapla
from backend.app.prebreakout.prebreakout_filters import gec_giris_riskleri
from backend.app.prebreakout.prebreakout_models import PreBreakoutConfig
from backend.tests.prebreakout_test_helpers import ornek_veri


def test_yuksek_son_gun_primi_gec_giris_sayilir() -> None:
    features = ozellikleri_hesapla(
        ornek_veri(son_gun_sicrama_pct=7.0)
    )
    risks = gec_giris_riskleri(features, PreBreakoutConfig())
    assert any("Son gün primi yüksek" in risk for risk in risks)


def test_kontrollu_hareket_gec_giris_uretmez() -> None:
    features = ozellikleri_hesapla(ornek_veri())
    risks = gec_giris_riskleri(features, PreBreakoutConfig())
    assert not any("Son gün primi yüksek" in risk for risk in risks)
