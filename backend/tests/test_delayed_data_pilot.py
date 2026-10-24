from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from backend.app.data.delayed_data_pilot import (
    ESKI_VERI_KILITLI,
    GUN_ICI_ON_IZLEME,
    GUNLUK_BAR_TAMAMLANDI,
    DelayedDataPilotConfig,
    DelayedDataPilotError,
    DelayedDataPilotStore,
    fetch_delayed_snapshot,
    pilot_to_csv,
)


ISTANBUL = ZoneInfo("Europe/Istanbul")


def frame(last_time: str, periods: int = 8) -> pd.DataFrame:
    index = pd.date_range(
        end=pd.Timestamp(last_time, tz=ISTANBUL),
        periods=periods,
        freq="5min",
    )
    return pd.DataFrame(
        {
            "Open": [100.0 + i for i in range(periods)],
            "High": [101.0 + i for i in range(periods)],
            "Low": [99.0 + i for i in range(periods)],
            "Close": [100.5 + i for i in range(periods)],
            "Volume": [1000.0 + i * 100 for i in range(periods)],
        },
        index=index,
    )


def downloader_for(data: pd.DataFrame):
    def downloader(**kwargs):
        return data.copy()
    return downloader


def test_seans_icinde_15_dakika_gecikmeli_veri_on_izlemedir():
    result = fetch_delayed_snapshot(
        "THYAO",
        now=datetime(2026, 7, 31, 14, 20, tzinfo=ISTANBUL),
        downloader=downloader_for(
            frame("2026-07-31 14:05")
        ),
    )

    assert result.symbol == "THYAO.IS"
    assert result.status == GUN_ICI_ON_IZLEME
    assert result.preview_only
    assert not result.locked
    assert result.measured_delay_minutes == 15.0


def test_gecikme_toleransi_asilirsa_kilitlenir():
    result = fetch_delayed_snapshot(
        "THYAO",
        now=datetime(2026, 7, 31, 14, 20, tzinfo=ISTANBUL),
        downloader=downloader_for(
            frame("2026-07-31 13:40")
        ),
    )

    assert result.status == ESKI_VERI_KILITLI
    assert result.locked


def test_kapanis_sonrasi_son_bar_tamamlanmis_sayilir():
    result = fetch_delayed_snapshot(
        "THYAO",
        now=datetime(2026, 7, 31, 18, 35, tzinfo=ISTANBUL),
        downloader=downloader_for(
            frame("2026-07-31 17:55")
        ),
    )

    assert result.status == GUNLUK_BAR_TAMAMLANDI
    assert result.latest_bar_completed
    assert not result.preview_only


def test_eksik_bar_sayisi_hesaplanir():
    data = frame("2026-07-31 14:05")
    data = data.drop(data.index[3])

    result = fetch_delayed_snapshot(
        "THYAO",
        now=datetime(2026, 7, 31, 14, 20, tzinfo=ISTANBUL),
        downloader=downloader_for(data),
    )

    assert result.missing_bar_count == 1


def test_store_jsonl_yazar_ve_okur(tmp_path: Path):
    result = fetch_delayed_snapshot(
        "THYAO",
        now=datetime(2026, 7, 31, 14, 20, tzinfo=ISTANBUL),
        downloader=downloader_for(
            frame("2026-07-31 14:05")
        ),
    )
    store = DelayedDataPilotStore(tmp_path)

    path = store.append(result)
    records = store.list()

    assert path.exists()
    assert len(records) == 1
    assert records[0].symbol == "THYAO.IS"


def test_csv_utf8_bom_ile_uretilir(tmp_path: Path):
    result = fetch_delayed_snapshot(
        "THYAO",
        now=datetime(2026, 7, 31, 14, 20, tzinfo=ISTANBUL),
        downloader=downloader_for(
            frame("2026-07-31 14:05")
        ),
    )
    store = DelayedDataPilotStore(tmp_path)
    store.append(result)

    content = pilot_to_csv(store.list())

    assert content.startswith(b"\xef\xbb\xbf")
    assert "THYAO.IS" in content.decode("utf-8-sig")


def test_yenileme_araligi_sinirlanir():
    with pytest.raises(
        DelayedDataPilotError,
        match="Yenileme aralığı",
    ):
        DelayedDataPilotConfig(refresh_interval_minutes=3)


def test_veri_kaynagi_hatasi_aciklanir():
    def failing(**kwargs):
        raise RuntimeError("network")

    with pytest.raises(
        DelayedDataPilotError,
        match="gecikmeli verisi alınamadı",
    ):
        fetch_delayed_snapshot(
            "THYAO",
            downloader=failing,
        )


def test_eksik_sutun_reddedilir():
    data = frame("2026-07-31 14:05").drop(columns=["Volume"])

    with pytest.raises(
        DelayedDataPilotError,
        match="Eksik gün içi veri sütunları",
    ):
        fetch_delayed_snapshot(
            "THYAO",
            now=datetime(2026, 7, 31, 14, 20, tzinfo=ISTANBUL),
            downloader=downloader_for(data),
        )
