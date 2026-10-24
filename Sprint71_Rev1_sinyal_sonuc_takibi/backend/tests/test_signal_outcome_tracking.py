from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from backend.app.analysis.signal_outcome_tracking import (
    SignalOutcomeError,
    SignalOutcomeJsonStore,
    SignalSnapshot,
    evaluate_signal,
    outcome_rows,
    outcomes_to_csv,
    success_summary,
)


def frame(length: int = 30) -> pd.DataFrame:
    index = pd.bdate_range("2026-01-02", periods=length)
    close = [100 + index_ for index_ in range(length)]
    return pd.DataFrame(
        {
            "Close": close,
            "High": [value + 1 for value in close],
            "Low": [value - 1 for value in close],
        },
        index=index,
    )


def snapshot(**changes) -> SignalSnapshot:
    values = {
        "symbol": "THYAO",
        "signal_date": date(2026, 1, 5),
        "reference_price": 101.0,
        "decision_class": "İzlemeye Değer",
        "quality_score": 78,
        "daily_direction": "Pozitif",
        "weekly_direction": "Pozitif",
        "divergence_type": "Normal Pozitif",
        "market_regime": "Olumlu",
        "sector": "Ulaştırma",
        "stop_loss": 98.0,
        "target_1": 106.0,
        "target_2": 112.0,
    }
    values.update(changes)
    return SignalSnapshot(**values)


def test_5_10_20_islem_gunu_sonuclari_hesaplanir():
    result = evaluate_signal(snapshot(), frame())

    assert [item.horizon for item in result.horizons] == [5, 10, 20]
    assert all(item.available for item in result.horizons)


def test_sinyal_tarihi_bari_performansa_dahil_edilmez():
    prices = frame()
    result = evaluate_signal(snapshot(), prices)
    first_five = result.horizons[0]

    expected_end = prices.loc[
        prices.index > pd.Timestamp("2026-01-05")
    ].iloc[:5].index[-1].date()

    assert first_five.end_date == expected_end


def test_yetersiz_gelecek_veri_tamamlanmamis_isaretlenir():
    result = evaluate_signal(snapshot(), frame(8))

    assert result.horizons[0].available
    assert not result.horizons[1].available
    assert not result.horizons[2].available


def test_mfe_mae_hedef_ve_stop_olculur():
    result = evaluate_signal(snapshot(), frame())
    horizon = result.horizons[-1]

    assert horizon.maximum_favorable_excursion_percent > 0
    assert horizon.maximum_adverse_excursion_percent is not None
    assert horizon.target_1_hit is True
    assert horizon.target_2_hit is True
    assert horizon.stop_hit is False


def test_store_kaydi_gunceller_ve_okur(tmp_path: Path):
    store = SignalOutcomeJsonStore(tmp_path)
    outcome = evaluate_signal(snapshot(), frame())

    first = store.save(outcome)
    second = store.save(outcome)
    loaded = store.list()

    assert first == second
    assert len(loaded) == 1
    assert loaded[0].snapshot.symbol == "THYAO.IS"


def test_basari_ozeti_tamamlanan_kayitlari_kullanir():
    outcomes = (
        evaluate_signal(snapshot(), frame()),
        evaluate_signal(
            snapshot(symbol="EREGL", reference_price=101.0),
            frame(),
        ),
    )

    summary = success_summary(outcomes, horizon=10)

    assert summary["Tamamlanan kayıt"] == 2
    assert summary["Pozitif kapanış oranı (%)"] == 100.0


def test_csv_utf8_bom_ile_uretilir():
    outcome = evaluate_signal(snapshot(), frame())

    content = outcomes_to_csv((outcome,))

    assert content.startswith(b"\xef\xbb\xbf")
    assert "THYAO.IS" in content.decode("utf-8-sig")


def test_tablo_satirlari_karar_ve_ufuk_bilgisi_icerir():
    rows = outcome_rows((evaluate_signal(snapshot(), frame()),))

    assert len(rows) == 3
    assert rows[0]["Karar sınıfı"] == "İzlemeye Değer"
    assert rows[0]["Ufuk"] == "5 işlem günü"


def test_eksik_fiyat_sutunlari_reddedilir():
    with pytest.raises(SignalOutcomeError, match="eksik sütunlar"):
        evaluate_signal(
            snapshot(),
            pd.DataFrame(
                {"Close": [100.0]},
                index=pd.to_datetime(["2026-01-06"]),
            ),
        )


def test_referans_fiyat_gecersizse_reddedilir():
    with pytest.raises(SignalOutcomeError, match="Referans fiyat"):
        snapshot(reference_price=0.0)
