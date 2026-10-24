from dataclasses import replace

from backend.app.prebreakout.prebreakout_features import ozellikleri_hesapla
from backend.app.prebreakout.prebreakout_models import PreBreakoutStage
from backend.app.prebreakout.prebreakout_stage import asamayi_belirle
from backend.tests.prebreakout_test_helpers import ornek_veri


def test_gec_giris_asamayi_hareket_baslamis_yapar() -> None:
    features = ozellikleri_hesapla(ornek_veri())
    stage = asamayi_belirle(85, features, late_entry=True)
    assert stage is PreBreakoutStage.HAREKET_BASLAMIS


def test_dusuk_skor_hazirlik_yoktur() -> None:
    features = ozellikleri_hesapla(ornek_veri())
    assert asamayi_belirle(40, features, late_entry=False) is PreBreakoutStage.HAZIRLIK_YOK


def test_e3_icin_dirence_yakinlik_gerekir() -> None:
    features = ozellikleri_hesapla(ornek_veri())
    far = replace(features, direnc_uzaklik_pct=12.0)
    assert asamayi_belirle(75, far, late_entry=False) is PreBreakoutStage.E2
