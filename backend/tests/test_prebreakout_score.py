from dataclasses import replace

from backend.app.prebreakout.prebreakout_features import ozellikleri_hesapla
from backend.app.prebreakout.prebreakout_score import skoru_hesapla
from backend.tests.prebreakout_test_helpers import ornek_veri


def test_skor_bilesenleri_tanimli_maksimumlari_asmaz() -> None:
    score = skoru_hesapla(ozellikleri_hesapla(ornek_veri()))
    assert 0 <= score.sikisma <= 20
    assert 0 <= score.momentum <= 20
    assert 0 <= score.trend <= 20
    assert 0 <= score.hacim <= 15
    assert 0 <= score.direnc <= 10
    assert 0 <= score.goreceli_guc <= 10
    assert 0 <= score.risk_odul <= 5
    assert 0 <= score.toplam <= 100


def test_goreceli_guc_skoru_toplama_yansir() -> None:
    features = ozellikleri_hesapla(ornek_veri())
    low = skoru_hesapla(features, relative_strength_score=2)
    high = skoru_hesapla(features, relative_strength_score=9)
    assert high.toplam - low.toplam == 7
