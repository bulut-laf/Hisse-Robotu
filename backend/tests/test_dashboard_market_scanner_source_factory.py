from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def test_manual_vbts_dataset_ile_korumali_tarama_servisi_olusturulur(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from backend.app.compliance.dashboard_market_scanner_source_factory import (
        build_dashboard_market_scanner,
    )

    csv_path = tmp_path / "vbts.csv"
    csv_path.write_text(
        "symbol,measure_type,start_date,end_date,source_reference\n"
        "BORLS,BRUT_TAKAS,2026-07-09,2026-08-07,1629762\n",
        encoding="utf-8",
    )

    monkeypatch.setenv(
        "HISSE_ROBOTU_VBTS_SOURCE",
        "manual_csv",
    )
    monkeypatch.setenv(
        "HISSE_ROBOTU_VBTS_CSV_PATH",
        str(csv_path),
    )
    monkeypatch.setenv(
        "HISSE_ROBOTU_VBTS_CSV_MAX_AGE_HOURS",
        "24",
    )

    now = datetime(
        2026,
        7,
        29,
        8,
        0,
        tzinfo=timezone.utc,
    )

    service = build_dashboard_market_scanner(
        now_provider=lambda: now,
    )

    assert service is not None


def test_vbts_kaynagi_tanimli_degilse_guvenli_durur(
    monkeypatch,
) -> None:
    from backend.app.compliance.dashboard_market_scanner_source_factory import (
        DashboardMarketScannerSourceError,
        build_dashboard_market_scanner,
    )

    monkeypatch.delenv(
        "HISSE_ROBOTU_VBTS_SOURCE",
        raising=False,
    )

    try:
        build_dashboard_market_scanner()
    except DashboardMarketScannerSourceError as exc:
        assert "VBTS veri kaynağı" in str(exc)
    else:
        raise AssertionError("Eksik VBTS kaynağında güvenli durdurma bekleniyordu.")


def test_desteklenmeyen_vbts_kaynagi_reddedilir(
    monkeypatch,
) -> None:
    from backend.app.compliance.dashboard_market_scanner_source_factory import (
        DashboardMarketScannerSourceError,
        build_dashboard_market_scanner,
    )

    monkeypatch.setenv(
        "HISSE_ROBOTU_VBTS_SOURCE",
        "bilinmeyen",
    )

    try:
        build_dashboard_market_scanner()
    except DashboardMarketScannerSourceError as exc:
        assert "desteklenmiyor" in str(exc)
    else:
        raise AssertionError("Desteklenmeyen VBTS kaynağı reddedilmeliydi.")
