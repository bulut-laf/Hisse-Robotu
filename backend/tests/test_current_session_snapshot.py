from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from backend.app.ui.current_session_snapshot import (
    CurrentSessionSnapshotError,
    guncel_seans_ozeti_getir,
)


def _veri() -> pd.DataFrame:
    index = pd.DatetimeIndex(
        [
            "2026-07-24 10:00:00+03:00",
            "2026-07-24 10:05:00+03:00",
            "2026-07-27 10:00:00+03:00",
            "2026-07-27 10:05:00+03:00",
            "2026-07-27 10:10:00+03:00",
        ]
    )
    return pd.DataFrame(
        {
            "Open": [340.0, 342.0, 350.0, 354.0, 357.0],
            "High": [343.0, 345.0, 354.5, 358.75, 358.0],
            "Low": [339.0, 341.0, 349.0, 353.0, 356.0],
            "Close": [342.0, 344.0, 354.0, 357.5, 357.75],
            "Volume": [100.0, 200.0, 300.0, 400.0, 500.0],
        },
        index=index,
    )


def test_guncel_seans_son_tarihi_ve_araligi_ozetler() -> None:
    def indirici(**_: object) -> pd.DataFrame:
        return _veri()

    sonuc = guncel_seans_ozeti_getir(
        "grsel.is",
        indirici=indirici,
        simdi=datetime(2026, 7, 27, 13, 0, tzinfo=ZoneInfo("Europe/Istanbul")),
    )

    assert sonuc.sembol == "GRSEL.IS"
    assert sonuc.seans_tarihi == "2026-07-27"
    assert sonuc.son_veri_zamani == "2026-07-27 10:10"
    assert sonuc.acilis == 350.0
    assert sonuc.en_yuksek == 358.75
    assert sonuc.en_dusuk == 349.0
    assert sonuc.son_fiyat == 357.75
    assert sonuc.hacim == 1200.0
    assert sonuc.bugunku_seans is True


def test_guncel_seans_sinyal_getirilerini_hesaplar() -> None:
    def indirici(**_: object) -> pd.DataFrame:
        return _veri()

    sonuc = guncel_seans_ozeti_getir(
        "GRSEL.IS",
        indirici=indirici,
        simdi=datetime(2026, 7, 27, 13, 0, tzinfo=ZoneInfo("Europe/Istanbul")),
    )

    assert sonuc.azami_getiri(315.75) == pytest.approx(358.75 / 315.75 - 1.0)
    assert sonuc.son_getiri(315.75) == pytest.approx(357.75 / 315.75 - 1.0)
    assert sonuc.azami_ters_hareket(315.75) == 0.0
    assert sonuc.azami_getiri(0.0) is None


def test_guncel_seans_multiindex_sutunlarini_duzeltir() -> None:
    veri = _veri().copy()
    veri.columns = pd.MultiIndex.from_tuples((sutun, "GRSEL.IS") for sutun in veri.columns)

    sonuc = guncel_seans_ozeti_getir(
        "GRSEL.IS",
        indirici=lambda **_: veri,
        simdi=datetime(2026, 7, 27, 13, 0, tzinfo=ZoneInfo("Europe/Istanbul")),
    )

    assert sonuc.en_yuksek == 358.75


def test_guncel_seans_bos_veride_acik_hata_verir() -> None:
    with pytest.raises(CurrentSessionSnapshotError, match="verisi bulunamadı"):
        guncel_seans_ozeti_getir(
            "GRSEL.IS",
            indirici=lambda **_: pd.DataFrame(),
        )


def test_guncel_seans_indirici_hatasini_sarmalar() -> None:
    def indirici(**_: object) -> pd.DataFrame:
        raise RuntimeError("bağlantı yok")

    with pytest.raises(CurrentSessionSnapshotError, match="bağlantı yok"):
        guncel_seans_ozeti_getir("GRSEL.IS", indirici=indirici)
