from datetime import date

import numpy as np
import pandas as pd
import pytest

from backend.app.prebreakout.prebreakout_validation import (
    PreBreakoutValidationConfig,
    dogrulama_ozeti,
    toplu_tarihsel_dogrulama,
    uygun_kesim_tarihleri,
)


def veri(offset: float = 0.0, gun: int = 140) -> pd.DataFrame:
    index = pd.bdate_range("2026-01-02", periods=gun)
    close = np.linspace(100.0 + offset, 118.0 + offset, gun)
    close += np.sin(np.linspace(0.0, 10.0, gun))
    spread = np.linspace(2.0, 1.0, gun)
    volume = np.full(gun, 2_000_000.0)
    volume[-30:] = 2_300_000.0

    return pd.DataFrame(
        {
            "Open": close - 0.2,
            "High": close + spread / 2,
            "Low": close - spread / 2,
            "Close": close,
            "Volume": volume,
        },
        index=index,
    )


def config() -> PreBreakoutValidationConfig:
    return PreBreakoutValidationConfig(
        start_date=date(2026, 4, 1),
        end_date=date(2026, 6, 30),
        cutoff_step=5,
        minimum_score=0,
    )


def test_config_gecersiz_tarih_araligini_reddeder() -> None:
    with pytest.raises(ValueError):
        PreBreakoutValidationConfig(
            start_date=date(2026, 7, 2),
            end_date=date(2026, 7, 1),
        )


def test_kesim_tarihleri_minimum_gecmis_ve_adimi_korur() -> None:
    dates = uygun_kesim_tarihleri(veri(), config())

    assert dates
    assert all(config().start_date <= item <= config().end_date for item in dates)


def test_toplu_dogrulama_deterministik_siralidir() -> None:
    data = {
        "B.IS": veri(3.0),
        "A.IS": veri(0.0),
    }

    first = toplu_tarihsel_dogrulama(data, config())
    second = toplu_tarihsel_dogrulama(data, config())

    assert first == second
    assert list(first) == sorted(
        first,
        key=lambda record: (record.cutoff_date, record.symbol),
    )


def test_minimum_skor_kayit_sayisini_filtreler() -> None:
    data = {"TEST.IS": veri()}
    low = toplu_tarihsel_dogrulama(data, config())

    high_config = PreBreakoutValidationConfig(
        start_date=config().start_date,
        end_date=config().end_date,
        cutoff_step=5,
        minimum_score=100,
    )
    high = toplu_tarihsel_dogrulama(data, high_config)

    assert len(low) >= len(high)
    assert high == ()


def test_dogrulama_ozeti_sayimlari_tutarlidir() -> None:
    records = toplu_tarihsel_dogrulama(
        {"TEST.IS": veri()},
        config(),
    )
    summary = dogrulama_ozeti(records)

    assert summary.total_replays == len(records)
    assert 0.0 <= summary.success_rate_pct <= 100.0
    assert 0.0 <= summary.false_positive_rate_pct <= 100.0
