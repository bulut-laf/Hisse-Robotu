from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from backend.app.data.bist_official_batch_bridge import (
    OfficialLatestDailyResult,
    merge_official_daily_bar,
)
from backend.app.data.batch_market_data import toplu_fiyat_verisi_getir


def _frame(dates, closes):
    closes = list(closes)
    return pd.DataFrame(
        {
            "Open": [x - 1 for x in closes],
            "High": [x + 2 for x in closes],
            "Low": [x - 2 for x in closes],
            "Close": closes,
            "Volume": [1_000_000] * len(closes),
        },
        index=pd.to_datetime(dates),
    )


def _multi(symbols, dates):
    columns = pd.MultiIndex.from_product(
        [symbols, ["Open", "High", "Low", "Close", "Volume"]]
    )
    data = pd.DataFrame(index=pd.to_datetime(dates), columns=columns, dtype=float)
    for i, symbol in enumerate(symbols):
        base = np.arange(len(dates), dtype=float) + 100 + i
        data[(symbol, "Open")] = base
        data[(symbol, "High")] = base + 2
        data[(symbol, "Low")] = base - 2
        data[(symbol, "Close")] = base + 1
        data[(symbol, "Volume")] = 1_000_000 + i
    return data


def test_merge_adds_missing_official_date():
    yahoo = _frame(["2026-07-30", "2026-07-31"], [100, 101])
    official = _frame(["2026-08-03"], [105])
    merged = merge_official_daily_bar(yahoo, official)
    assert list(merged.index.date) == [
        date(2026, 7, 30),
        date(2026, 7, 31),
        date(2026, 8, 3),
    ]


def test_merge_official_wins_same_date():
    yahoo = _frame(["2026-08-03"], [999])
    official = _frame(["2026-08-03"], [317])
    merged = merge_official_daily_bar(yahoo, official)
    assert len(merged) == 1
    assert merged.iloc[-1]["Close"] == pytest.approx(317)


def test_merge_respects_max_rows():
    yahoo = _frame(
        ["2026-07-29", "2026-07-30", "2026-07-31"],
        [99, 100, 101],
    )
    official = _frame(["2026-08-03"], [105])
    merged = merge_official_daily_bar(yahoo, official, max_rows=3)
    assert list(merged.index.date) == [
        date(2026, 7, 30),
        date(2026, 7, 31),
        date(2026, 8, 3),
    ]


def test_batch_merges_official_once_for_all_symbols():
    symbols = ["THYAO.IS", "ASELS.IS"]
    dates = pd.bdate_range("2025-12-22", periods=160)
    calls = {"official": 0}

    def downloader(**kwargs):
        return _multi(list(kwargs["tickers"]), dates)

    def official_loader(requested, today):
        calls["official"] += 1
        assert tuple(requested) == tuple(symbols)
        return OfficialLatestDailyResult(
            islem_tarihi=date(2026, 8, 3),
            veriler={
                "THYAO.IS": _frame(["2026-08-03"], [317]),
                "ASELS.IS": _frame(["2026-08-03"], [336.25]),
            },
            kaynak="bist_resmi_arsiv",
        )

    result = toplu_fiyat_verisi_getir(
        symbols,
        islem_gunu=160,
        indirici=downloader,
        bugun=date(2026, 8, 4),
        resmi_gunluk_yukleyici=official_loader,
        resmi_veriyi_birlestir=True,
    )

    assert calls["official"] == 1
    assert result.veriler["THYAO.IS"].index[-1] == pd.Timestamp("2026-08-03")
    assert result.veriler["THYAO.IS"].iloc[-1]["Close"] == pytest.approx(317)
    assert result.veriler["ASELS.IS"].iloc[-1]["Close"] == pytest.approx(336.25)
    assert result.kaynak_sirasi == ("yahoo", "bist_resmi_arsiv")


def test_official_failure_does_not_destroy_yahoo_history():
    dates = pd.bdate_range("2025-12-22", periods=160)

    def downloader(**kwargs):
        return _multi(["THYAO.IS"], dates)

    def official_loader(requested, today):
        raise RuntimeError("resmî ağ yok")

    result = toplu_fiyat_verisi_getir(
        ["THYAO.IS"],
        islem_gunu=160,
        parca_boyutu=1,
        indirici=downloader,
        bugun=date(2026, 8, 4),
        resmi_gunluk_yukleyici=official_loader,
        resmi_veriyi_birlestir=True,
    )

    assert "THYAO.IS" in result.veriler
    assert any("resmî ağ yok" in x for x in result.kaynak_hatalari)


def test_custom_downloader_keeps_official_auto_disabled():
    dates = pd.bdate_range("2025-12-22", periods=160)

    def downloader(**kwargs):
        return _multi(["THYAO.IS"], dates)

    result = toplu_fiyat_verisi_getir(
        ["THYAO.IS"],
        islem_gunu=160,
        parca_boyutu=1,
        indirici=downloader,
        bugun=date(2026, 8, 4),
    )

    assert result.kaynak_sirasi == ("yahoo",)
