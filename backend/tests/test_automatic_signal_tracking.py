from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from backend.app.analysis.automatic_signal_tracking import (
    automatic_record_from_values,
    save_or_update_signal,
    update_all_signal_outcomes,
)
from backend.app.analysis.signal_outcome_tracking import (
    SignalOutcomeJsonStore,
    SignalSnapshot,
)


def price_frame(periods: int) -> pd.DataFrame:
    index = pd.bdate_range("2026-07-01", periods=periods)
    return pd.DataFrame(
        {
            "Close": [100.0 + i for i in range(periods)],
            "High": [101.0 + i for i in range(periods)],
            "Low": [99.0 + i for i in range(periods)],
        },
        index=index,
    )


def downloader_for(frame: pd.DataFrame):
    def downloader(**kwargs):
        return frame.copy()
    return downloader


def snapshot() -> SignalSnapshot:
    return SignalSnapshot(
        symbol="THYAO",
        signal_date=date(2026, 7, 1),
        reference_price=100.0,
        decision_class="İzlemeye Değer",
        quality_score=75,
        daily_direction="Pozitif",
        weekly_direction="Pozitif",
    )


def test_yeni_sinyal_otomatik_kaydedilir(tmp_path: Path):
    store = SignalOutcomeJsonStore(tmp_path)

    result = save_or_update_signal(
        snapshot(),
        price_frame(8),
        store=store,
    )

    assert result.created
    assert not result.updated
    assert len(store.list()) == 1


def test_ayni_sembol_ve_tarih_mukerrer_kayit_uretmez(tmp_path: Path):
    store = SignalOutcomeJsonStore(tmp_path)

    first = save_or_update_signal(
        snapshot(),
        price_frame(8),
        store=store,
    )
    second = save_or_update_signal(
        snapshot(),
        price_frame(8),
        store=store,
    )

    assert first.created
    assert not second.created
    assert not second.updated
    assert len(store.list()) == 1


def test_yeni_gelecek_verisi_geldiginde_kayit_guncellenir(tmp_path: Path):
    store = SignalOutcomeJsonStore(tmp_path)
    save_or_update_signal(
        snapshot(),
        price_frame(8),
        store=store,
    )

    result = save_or_update_signal(
        snapshot(),
        price_frame(25),
        store=store,
    )

    assert result.updated
    stored = store.list()[0]
    assert stored.completed_horizons == 3


def test_tum_kayitlar_tek_islemle_guncellenir(tmp_path: Path):
    store = SignalOutcomeJsonStore(tmp_path)
    save_or_update_signal(
        snapshot(),
        price_frame(8),
        store=store,
    )

    summary = update_all_signal_outcomes(
        store=store,
        downloader=downloader_for(price_frame(25)),
        today=date(2026, 8, 31),
    )

    assert summary.total_records == 1
    assert summary.updated_records == 1
    assert summary.completed_horizons == 3
    assert summary.pending_horizons == 0


def test_eksik_gelecek_verisi_beklemede_kalir(tmp_path: Path):
    store = SignalOutcomeJsonStore(tmp_path)

    result = automatic_record_from_values(
        symbol="THYAO",
        signal_date=date(2026, 7, 1),
        reference_price=100.0,
        decision_class="Temkinli İzle",
        quality_score=60,
        daily_direction="Nötr",
        weekly_direction="Pozitif",
        store=store,
        downloader=downloader_for(price_frame(4)),
        today=date(2026, 7, 8),
    )

    assert result.outcome.completed_horizons == 0
    assert all(
        not horizon.available
        for horizon in result.outcome.horizons
    )


def test_hata_bir_kaydi_digerlerinden_ayirir(tmp_path: Path):
    store = SignalOutcomeJsonStore(tmp_path)
    save_or_update_signal(
        snapshot(),
        price_frame(8),
        store=store,
    )

    def failing(**kwargs):
        raise RuntimeError("network")

    summary = update_all_signal_outcomes(
        store=store,
        downloader=failing,
    )

    assert summary.failed_records == 1
    assert summary.total_records == 1
    assert summary.errors
