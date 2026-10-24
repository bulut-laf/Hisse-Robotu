from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pytest

from backend.app.compliance.dashboard_vbts_manager import (
    DashboardVbtsManagerError,
    add_vbts_record,
    build_vbts_record,
    delete_vbts_record,
    list_vbts_records,
)


def _record(reference: str = "1234567"):
    return build_vbts_record(
        symbol=" thyao ",
        measure_type="  Açığa satış yasağı ",
        start_date=" 2026-07-29 ",
        end_date=" 2026-08-28 ",
        source_reference=reference,
    )


def test_kayit_alanlarini_temizler_ve_sembolu_normalize_eder() -> None:
    record = _record()
    assert record.symbol == "THYAO.IS"
    assert record.measure_type == "Açığa satış yasağı"
    assert record.start_date == date(2026, 7, 29)


def test_ornek_kap_referansini_reddeder() -> None:
    with pytest.raises(DashboardVbtsManagerError, match="gerçek resmî KAP"):
        _record("KAP bildirim numarası")


def test_bitis_tarihi_baslangictan_once_olamaz() -> None:
    with pytest.raises(DashboardVbtsManagerError, match="önce olamaz"):
        build_vbts_record(
            symbol="THYAO",
            measure_type="Tedbir",
            start_date="2026-08-28",
            end_date="2026-07-29",
            source_reference="1234567",
        )


def test_kayit_ekleme_csvyi_olusturur_ve_kaynagi_etkinlestirir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    monkeypatch.delenv("HISSE_ROBOTU_VBTS_SOURCE", raising=False)
    monkeypatch.delenv("HISSE_ROBOTU_VBTS_CSV_PATH", raising=False)

    # P0_DATE_ROT_FIX_V3
    records = add_vbts_record(csv_path, __import__("dataclasses").replace(_record(), start_date=__import__("datetime").date.today() - __import__("datetime").timedelta(days=1), end_date=__import__("datetime").date.today() + __import__("datetime").timedelta(days=30)))

    assert len(records) == 1
    assert csv_path.exists()
    assert os.environ["HISSE_ROBOTU_VBTS_SOURCE"] == "manual_csv"
    assert os.environ["HISSE_ROBOTU_VBTS_CSV_PATH"] == str(csv_path)


def test_ayni_kaydi_ikinci_kez_eklemez(tmp_path: Path) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    record = _record()
    add_vbts_record(csv_path, record)

    with pytest.raises(DashboardVbtsManagerError, match="zaten mevcut"):
        add_vbts_record(csv_path, record)


def test_son_kayit_silinince_csv_dosyasi_kaldirilir(tmp_path: Path) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    record = _record()
    add_vbts_record(csv_path, record)

    remaining = delete_vbts_record(csv_path, record.record_key)

    assert remaining == ()
    assert not csv_path.exists()


def test_kayitlar_yeniden_okunabilir(tmp_path: Path) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    record = _record()
    add_vbts_record(csv_path, record)
    assert list_vbts_records(csv_path) == (record,)
