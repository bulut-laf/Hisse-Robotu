import pytest

from backend.app.prebreakout.prebreakout_features import (
    PreBreakoutDataError,
    ozellikleri_hesapla,
)
from backend.tests.prebreakout_test_helpers import ornek_veri


def test_ozellikler_temel_teknik_degerleri_uretir() -> None:
    features = ozellikleri_hesapla(ornek_veri())
    assert features.close > 0
    assert features.ema9 > 0
    assert 0 <= features.rsi14 <= 100
    assert features.atr14 > 0
    assert features.direnc > 0


def test_daralan_fiyat_araligi_yakalanir() -> None:
    features = ozellikleri_hesapla(ornek_veri())
    assert features.bes_gun_aralik_daralma_orani < 1.0


def test_yetersiz_bar_reddedilir() -> None:
    with pytest.raises(PreBreakoutDataError):
        ozellikleri_hesapla(ornek_veri(gun=40))


def test_eksik_ohlcv_sutunu_reddedilir() -> None:
    data = ornek_veri().drop(columns=["Volume"])
    with pytest.raises(PreBreakoutDataError):
        ozellikleri_hesapla(data)
