from datetime import date

import numpy as np
import pandas as pd

from backend.app.prebreakout.prebreakout_validation import (
    PreBreakoutValidationConfig,
    dogrulama_ozeti,
    toplu_tarihsel_dogrulama,
)
from backend.app.prebreakout.prebreakout_validation_report import (
    asama_bazli_ozet,
    dogrulama_kayitlarini_tabloya_cevir,
    dogrulama_ozetini_tabloya_cevir,
)


def veri() -> pd.DataFrame:
    index = pd.bdate_range("2026-01-02", periods=140)
    close = np.linspace(100.0, 118.0, 140)
    return pd.DataFrame(
        {
            "Open": close - 0.2,
            "High": close + 0.8,
            "Low": close - 0.8,
            "Close": close,
            "Volume": np.full(140, 2_000_000.0),
        },
        index=index,
    )


def test_dogrulama_raporu_ileri_performans_sutunlari_icerir() -> None:
    config = PreBreakoutValidationConfig(
        start_date=date(2026, 4, 1),
        end_date=date(2026, 5, 30),
        cutoff_step=10,
        minimum_score=0,
    )
    records = toplu_tarihsel_dogrulama(
        {"TEST.IS": veri()},
        config,
    )

    table = dogrulama_kayitlarini_tabloya_cevir(records)

    assert "performance_label" in table.columns
    assert "max_return_20d_pct" in table.columns


def test_ozet_ve_asama_tablolari_uretilir() -> None:
    config = PreBreakoutValidationConfig(
        start_date=date(2026, 4, 1),
        end_date=date(2026, 5, 30),
        cutoff_step=10,
        minimum_score=0,
    )
    records = toplu_tarihsel_dogrulama(
        {"TEST.IS": veri()},
        config,
    )
    summary = dogrulama_ozeti(records)

    summary_table = dogrulama_ozetini_tabloya_cevir(summary)
    stage_table = asama_bazli_ozet(records)

    assert len(summary_table) == 1
    assert "success_rate_pct" in summary_table.columns
    assert "stage" in stage_table.columns
