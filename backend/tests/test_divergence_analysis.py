from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend.app.analysis.divergence_analysis import (
    DivergenceAnalysisError,
    DivergenceKind,
    _classify_pair,
    PivotPoint,
    analyze_divergences,
    divergence_rows,
)


def point(position: int, price: float, oscillator: float) -> PivotPoint:
    return PivotPoint(
        position=position,
        timestamp=pd.Timestamp("2026-01-01") + pd.Timedelta(days=position),
        price=price,
        oscillator=oscillator,
    )


@pytest.mark.parametrize(
    ("mode", "first", "second", "expected"),
    (
        (
            "low",
            point(1, 100, 30),
            point(10, 95, 38),
            DivergenceKind.NORMAL_POSITIVE,
        ),
        (
            "high",
            point(1, 100, 70),
            point(10, 106, 60),
            DivergenceKind.NORMAL_NEGATIVE,
        ),
        (
            "low",
            point(1, 100, 35),
            point(10, 105, 29),
            DivergenceKind.HIDDEN_POSITIVE,
        ),
        (
            "high",
            point(1, 100, 65),
            point(10, 95, 72),
            DivergenceKind.HIDDEN_NEGATIVE,
        ),
    ),
)
def test_dort_uyumsuzluk_turu_siniflandirilir(
    mode,
    first,
    second,
    expected,
):
    result = _classify_pair(
        first,
        second,
        mode=mode,
        minimum_price_change_percent=1.0,
        minimum_oscillator_change=3.0,
    )

    assert result == expected


def test_zayif_fark_uyumsuzluk_sayilmaz():
    result = _classify_pair(
        point(1, 100, 30),
        point(10, 99.5, 31),
        mode="low",
        minimum_price_change_percent=1.0,
        minimum_oscillator_change=3.0,
    )

    assert result is None


def frame(length: int = 120) -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=length, freq="D")
    x = np.linspace(0, 8 * np.pi, length)
    close = 100 + np.sin(x) * 8 + np.linspace(0, 4, length)
    volume = 1_000_000 + (np.cos(x) + 1) * 200_000
    return pd.DataFrame(
        {
            "Open": close - 0.5,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": volume,
        },
        index=index,
    )


def test_analiz_tamamlanmis_veride_guvenli_sonuc_uretir():
    result = analyze_divergences(
        frame(),
        timeframe="Günlük",
    )

    assert result.timeframe == "Günlük"
    assert result.latest_timestamp == frame().index[-1]
    assert result.positive_count >= 0
    assert result.negative_count >= 0
    assert "tek başına alım/satım sinyali değildir" in result.disclaimer


def test_yetersiz_veri_reddedilir():
    with pytest.raises(
        DivergenceAnalysisError,
        match="en az 45",
    ):
        analyze_divergences(
            frame(30),
            timeframe="Günlük",
        )


def test_tarih_sirasi_bozuk_veri_reddedilir():
    data = frame().sort_index(ascending=False)

    with pytest.raises(
        DivergenceAnalysisError,
        match="tarih sırasına",
    ):
        analyze_divergences(
            data,
            timeframe="Günlük",
        )


def test_tablo_satirlari_uretilir():
    result = analyze_divergences(
        frame(),
        timeframe="Günlük",
    )

    rows = divergence_rows((result,))

    assert isinstance(rows, list)
    if rows:
        assert "Uyumsuzluk" in rows[0]
        assert "Güven skoru" in rows[0]
