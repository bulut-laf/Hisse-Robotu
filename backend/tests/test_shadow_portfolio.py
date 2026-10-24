from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from backend.app.analysis.shadow_portfolio import (
    CLOSED_STATUS,
    OPEN_STATUS,
    ShadowPortfolioError,
    ShadowPortfolioStore,
    close_shadow_position,
    open_shadow_position,
    position_rows,
    positions_to_csv,
    refresh_position,
)


def history() -> pd.DataFrame:
    index = pd.bdate_range("2026-07-01", periods=8)
    return pd.DataFrame(
        {
            "Close": [100, 102, 101, 104, 103, 106, 105, 107],
            "High": [101, 103, 102, 105, 104, 107, 106, 108],
            "Low": [99, 100, 98, 101, 100, 102, 101, 103],
        },
        index=index,
    )


def open_position(store: ShadowPortfolioStore):
    return open_shadow_position(
        store=store,
        symbol="THYAO",
        entry_date=date(2026, 7, 1),
        entry_price=100.0,
        quantity=100,
        capital_at_entry=100000.0,
        stop_loss=95.0,
        target_1=105.0,
        target_2=110.0,
        rationale="Kalibrasyon",
    )


def test_golge_pozisyon_acilir_ve_json_saklanir(tmp_path: Path):
    store = ShadowPortfolioStore(tmp_path / "portfolio.json")
    position = open_position(store)

    assert position.status == OPEN_STATUS
    assert len(store.list()) == 1
    assert store.file_path.exists()


def test_ayni_sembolde_ikinci_acik_pozisyon_engellenir(tmp_path: Path):
    store = ShadowPortfolioStore(tmp_path / "portfolio.json")
    open_position(store)

    with pytest.raises(
        ShadowPortfolioError,
        match="açık gölge pozisyon zaten var",
    ):
        open_position(store)


def test_fiyat_guncellemesi_mfe_mae_hedef_ve_stop_hesaplar(tmp_path: Path):
    store = ShadowPortfolioStore(tmp_path / "portfolio.json")
    position = open_position(store)

    updated = refresh_position(
        position,
        history(),
        store=store,
    )

    assert updated.last_price == 107.0
    assert updated.mfe_percent == 8.0
    assert updated.mae_percent == -2.0
    assert updated.target_1_hit
    assert not updated.target_2_hit
    assert not updated.stop_hit
    assert updated.unrealized_pnl == 700.0


def test_pozisyon_kapatilinca_gerceklesen_kar_hesaplanir(tmp_path: Path):
    store = ShadowPortfolioStore(tmp_path / "portfolio.json")
    position = open_position(store)

    closed = close_shadow_position(
        position,
        store=store,
        exit_date=date(2026, 7, 15),
        exit_price=108.0,
        close_reason="Hedefe yaklaştı",
        fees=20.0,
    )

    assert closed.status == CLOSED_STATUS
    assert closed.realized_pnl == 780.0
    assert closed.unrealized_pnl == 0.0
    assert closed.return_percent == 7.8


def test_csv_utf8_bom_ile_uretilir(tmp_path: Path):
    store = ShadowPortfolioStore(tmp_path / "portfolio.json")
    open_position(store)

    content = positions_to_csv(store.list())

    assert content.startswith(b"\xef\xbb\xbf")
    assert "THYAO.IS" in content.decode("utf-8-sig")


def test_portfoy_tablo_satirlari_acik_ve_kapali_durumu_gosterir(tmp_path: Path):
    store = ShadowPortfolioStore(tmp_path / "portfolio.json")
    position = open_position(store)
    close_shadow_position(
        position,
        store=store,
        exit_date=date(2026, 7, 15),
        exit_price=108.0,
        close_reason="Test",
    )

    rows = position_rows(store.list())

    assert rows[0]["Durum"] == CLOSED_STATUS
    assert "Gerçekleşen K/Z" in rows[0]
