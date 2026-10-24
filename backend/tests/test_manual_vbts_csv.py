from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest


def test_resmi_vbts_csv_gecerli_dataset_uretir(tmp_path: Path) -> None:
    from backend.app.compliance.manual_vbts_csv import (
        load_official_vbts_csv,
    )

    csv_path = tmp_path / "vbts.csv"
    csv_path.write_text(
        "symbol,measure_type,start_date,end_date,source_reference\n"
        "BORLS,BRUT_TAKAS,2026-07-09,2026-08-07,1629762\n"
        "XYZ,EMIR_PAKETI,2026-07-28,2026-08-27,1630000\n",
        encoding="utf-8",
    )

    fetched_at = datetime(
        2026,
        7,
        29,
        8,
        0,
        tzinfo=timezone.utc,
    )

    dataset = load_official_vbts_csv(
        csv_path,
        fetched_at=fetched_at,
        maximum_file_age=timedelta(hours=24),
        now_provider=lambda: fetched_at,
    )

    assert dataset.status.source == "KAP_MANUEL_CSV"
    assert dataset.status.is_verified is True
    assert dataset.status.record_count == 2
    assert dataset.measures[0].symbol == "BORLS.IS"
    assert dataset.measures[0].source_reference == "1629762"


def test_resmi_vbts_csv_zorunlu_sutun_eksikse_reddedilir(
    tmp_path: Path,
) -> None:
    from backend.app.compliance.manual_vbts_csv import (
        ManualVbtsCsvError,
        load_official_vbts_csv,
    )

    csv_path = tmp_path / "vbts.csv"
    csv_path.write_text(
        "symbol,start_date,end_date\n"
        "BORLS,2026-07-09,2026-08-07\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ManualVbtsCsvError,
        match="zorunlu sütun",
    ):
        load_official_vbts_csv(
            csv_path,
            fetched_at=datetime.now(timezone.utc),
        )


def test_resmi_vbts_csv_eski_dosyayi_guvenli_bicimde_reddeder(
    tmp_path: Path,
) -> None:
    from backend.app.compliance.manual_vbts_csv import (
        ManualVbtsCsvError,
        load_official_vbts_csv,
    )

    csv_path = tmp_path / "vbts.csv"
    csv_path.write_text(
        "symbol,measure_type,start_date,end_date,source_reference\n"
        "BORLS,BRUT_TAKAS,2026-07-09,2026-08-07,1629762\n",
        encoding="utf-8",
    )

    old_time = datetime(
        2026,
        7,
        27,
        8,
        0,
        tzinfo=timezone.utc,
    ).timestamp()

    import os

    os.utime(csv_path, (old_time, old_time))

    now = datetime(
        2026,
        7,
        29,
        8,
        0,
        tzinfo=timezone.utc,
    )

    with pytest.raises(
        ManualVbtsCsvError,
        match="güncel değil",
    ):
        load_official_vbts_csv(
            csv_path,
            fetched_at=now,
            maximum_file_age=timedelta(hours=24),
            now_provider=lambda: now,
        )


def test_resmi_vbts_csv_tarih_araligi_hatalıysa_reddedilir(
    tmp_path: Path,
) -> None:
    from backend.app.compliance.manual_vbts_csv import (
        ManualVbtsCsvError,
        load_official_vbts_csv,
    )

    csv_path = tmp_path / "vbts.csv"
    csv_path.write_text(
        "symbol,measure_type,start_date,end_date,source_reference\n"
        "BORLS,BRUT_TAKAS,2026-08-07,2026-07-09,1629762\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ManualVbtsCsvError,
        match="bitiş tarihi",
    ):
        load_official_vbts_csv(
            csv_path,
            fetched_at=datetime.now(timezone.utc),
        )
