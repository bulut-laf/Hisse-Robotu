from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path


def test_dashboard_manual_vbts_csv_ayarini_okur(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from backend.app.compliance.dashboard_manual_vbts import (
        load_dashboard_vbts_dataset,
    )

    csv_path = tmp_path / "vbts.csv"
    csv_path.write_text(
        "symbol,measure_type,start_date,end_date,source_reference\n"
        "BORLS,BRUT_TAKAS,2026-07-09,2026-08-07,1629762\n",
        encoding="utf-8",
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

    dataset = load_dashboard_vbts_dataset(
        now_provider=lambda: now,
    )

    assert dataset.status.source == "KAP_MANUEL_CSV"
    assert dataset.status.record_count == 1
    assert dataset.measures[0].symbol == "BORLS.IS"


def test_dashboard_manual_vbts_csv_yolu_eksikse_guvenli_durur(
    monkeypatch,
) -> None:
    from backend.app.compliance.dashboard_manual_vbts import (
        DashboardManualVbtsError,
        load_dashboard_vbts_dataset,
    )

    monkeypatch.delenv(
        "HISSE_ROBOTU_VBTS_CSV_PATH",
        raising=False,
    )

    try:
        load_dashboard_vbts_dataset()
    except DashboardManualVbtsError as exc:
        assert "VBTS CSV yolu" in str(exc)
    else:
        raise AssertionError("Eksik CSV yolunda güvenli durdurma bekleniyordu.")


def test_dashboard_manual_vbts_csv_azami_yasi_sayisal_degilse_reddedilir(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from backend.app.compliance.dashboard_manual_vbts import (
        DashboardManualVbtsError,
        load_dashboard_vbts_dataset,
    )

    csv_path = tmp_path / "vbts.csv"
    csv_path.write_text(
        "symbol,measure_type,start_date,end_date,source_reference\n"
        "BORLS,BRUT_TAKAS,2026-07-09,2026-08-07,1629762\n",
        encoding="utf-8",
    )

    monkeypatch.setenv(
        "HISSE_ROBOTU_VBTS_CSV_PATH",
        str(csv_path),
    )
    monkeypatch.setenv(
        "HISSE_ROBOTU_VBTS_CSV_MAX_AGE_HOURS",
        "yanlis",
    )

    try:
        load_dashboard_vbts_dataset()
    except DashboardManualVbtsError as exc:
        assert "azami yaşı" in str(exc)
    else:
        raise AssertionError("Geçersiz azami yaşta hata bekleniyordu.")


def test_dashboard_manual_vbts_csv_eski_dosyayi_reddeder(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from backend.app.compliance.dashboard_manual_vbts import (
        DashboardManualVbtsError,
        load_dashboard_vbts_dataset,
    )

    csv_path = tmp_path / "vbts.csv"
    csv_path.write_text(
        "symbol,measure_type,start_date,end_date,source_reference\n"
        "BORLS,BRUT_TAKAS,2026-07-09,2026-08-07,1629762\n",
        encoding="utf-8",
    )

    old = datetime(
        2026,
        7,
        27,
        8,
        0,
        tzinfo=timezone.utc,
    ).timestamp()

    import os

    os.utime(csv_path, (old, old))

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

    try:
        load_dashboard_vbts_dataset(
            now_provider=lambda: now,
        )
    except DashboardManualVbtsError as exc:
        assert "güncel değil" in str(exc)
    else:
        raise AssertionError("Eski VBTS CSV dosyası reddedilmeliydi.")
