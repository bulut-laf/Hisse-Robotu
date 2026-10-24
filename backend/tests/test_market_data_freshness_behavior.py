from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from backend.app.data.market_data import (
    _bugunun_satirini_cikar,
    fiyat_verisini_duzelt,
)


def test_seans_oncesi_bugunku_bar_analizdan_cikarilir():
    veri = pd.DataFrame(
        {
            "Open": [311.0, 317.0],
            "High": [315.5, 319.25],
            "Low": [305.25, 314.5],
            "Close": [308.25, 315.75],
            "Volume": [41895470, 8483489],
        },
        index=pd.to_datetime(
            [
                "2026-08-03",
                "2026-08-04",
            ]
        ),
    )

    sonuc = _bugunun_satirini_cikar(
        veri,
        simdi=datetime(
            2026,
            8,
            4,
            10,
            30,
            tzinfo=ZoneInfo("Europe/Istanbul"),
        ),
    )

    assert sonuc.index[-1].date().isoformat() == "2026-08-03"


def test_seans_sonrasi_bugunku_bar_korunur():
    veri = pd.DataFrame(
        {
            "Open": [311.0, 317.0],
            "High": [315.5, 319.25],
            "Low": [305.25, 314.5],
            "Close": [308.25, 315.75],
            "Volume": [41895470, 8483489],
        },
        index=pd.to_datetime(
            [
                "2026-08-03",
                "2026-08-04",
            ]
        ),
    )

    sonuc = _bugunun_satirini_cikar(
        veri,
        simdi=datetime(
            2026,
            8,
            4,
            19,
            0,
            tzinfo=ZoneInfo("Europe/Istanbul"),
        ),
    )

    assert sonuc.index[-1].date().isoformat() == "2026-08-04"


def test_eksik_ohlc_bar_temizlenir():
    veri = pd.DataFrame(
        {
            "Open": [311.0, None],
            "High": [315.5, None],
            "Low": [305.25, None],
            "Close": [308.25, None],
            "Volume": [41895470, 46594813],
        },
        index=pd.to_datetime(
            [
                "2026-07-30",
                "2026-08-03",
            ]
        ),
    )

    sonuc = fiyat_verisini_duzelt(veri)

    assert len(sonuc) == 1
    assert sonuc.index[-1].date().isoformat() == "2026-07-30"