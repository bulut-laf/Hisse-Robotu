from __future__ import annotations

import pandas as pd

from backend.app.analysis.bist_daily_market import _gunluk_satir


def test_gunluk_satir_hesabi() -> None:
    frame = pd.DataFrame(
        {
            "Open": [10.0, 11.0],
            "High": [11.0, 12.0],
            "Low": [9.0, 10.5],
            "Close": [10.0, 11.0],
            "Volume": [1000.0, 1500.0],
        },
        index=pd.to_datetime(["2026-08-13", "2026-08-14"]),
    )
    row = _gunluk_satir("TEST.IS", frame)
    assert row is not None
    assert row["Hisse"] == "TEST"
    assert row["Son Fiyat"] == 11.0
    assert row["Önceki Kapanış"] == 10.0
    assert row["Günlük Değişim TL"] == 1.0
    assert row["Günlük Değişim %"] == 10.0
    assert row["En Düşük"] == 10.5
    assert row["En Yüksek"] == 12.0
    assert row["Veri Tarihi"] == "2026-08-14"


def test_gunluk_satir_en_az_iki_gun_ister() -> None:
    frame = pd.DataFrame(
        {"Open":[10.0], "High":[11.0], "Low":[9.0], "Close":[10.0], "Volume":[1000.0]},
        index=pd.to_datetime(["2026-08-14"]),
    )
    assert _gunluk_satir("TEST.IS", frame) is None
