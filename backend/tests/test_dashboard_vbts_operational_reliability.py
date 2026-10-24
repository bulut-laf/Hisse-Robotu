from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from backend.app.compliance.dashboard_vbts_manager import (
    DashboardVbtsManagerError,
    add_vbts_record,
    audit_log_path_for,
    backup_directory_for,
    build_vbts_record,
    delete_vbts_record,
    purge_expired_vbts_records,
    read_operational_status,
    synchronize_vbts_operational_state,
    synchronization_state_path_for,
)


def _record(symbol: str, start: str, end: str, ref: str):
    return build_vbts_record(
        symbol=symbol,
        measure_type="Tedbir",
        start_date=start,
        end_date=end,
        source_reference=ref,
    )


def test_uygulama_acilis_senkronizasyonu_durum_dosyasi_yazar(tmp_path: Path) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    add_vbts_record(
        csv_path,
        _record("THYAO", "2026-07-01", "2026-07-31", "KAP-1"),
    )

    lifecycle = synchronize_vbts_operational_state(
        csv_path,
        date(2026, 7, 29),
    )

    assert len(lifecycle.active) == 1
    assert synchronization_state_path_for(csv_path).exists()


def test_gun_degisiminde_gelecek_kayit_aktiflesir(tmp_path: Path) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    add_vbts_record(
        csv_path,
        _record("ASELS", "2026-07-30", "2026-08-30", "KAP-2"),
    )

    before = synchronize_vbts_operational_state(csv_path, date(2026, 7, 29))
    after = synchronize_vbts_operational_state(csv_path, date(2026, 7, 30))

    assert len(before.future) == 1
    assert len(after.active) == 1


def test_suresi_dolan_kayit_aktif_csvden_cikar(tmp_path: Path) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    add_vbts_record(
        csv_path,
        _record("TUPRS", "2026-07-01", "2026-07-29", "KAP-3"),
    )

    lifecycle = synchronize_vbts_operational_state(
        csv_path,
        date(2026, 7, 30),
    )

    assert len(lifecycle.expired) == 1
    assert not csv_path.exists()


def test_ekleme_silme_temizlik_denetim_gunlugune_yazilir(tmp_path: Path) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    active = _record("THYAO", "2026-07-01", "2026-07-31", "KAP-1")
    expired = _record("TUPRS", "2026-06-01", "2026-06-30", "KAP-3")

    add_vbts_record(csv_path, active)
    add_vbts_record(csv_path, expired)
    delete_vbts_record(csv_path, active.record_key)
    purge_expired_vbts_records(csv_path, date(2026, 7, 29))

    text = audit_log_path_for(csv_path).read_text(encoding="utf-8")
    assert "KAYIT_EKLENDI" in text
    assert "KAYIT_SILINDI" in text
    assert "SURESI_DOLMUS_KAYITLAR_TEMIZLENDI" in text


def test_degisimden_once_yedek_olusturulur(tmp_path: Path) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    first = _record("THYAO", "2026-07-01", "2026-07-31", "KAP-1")
    second = _record("ASELS", "2026-07-01", "2026-07-31", "KAP-2")

    add_vbts_record(csv_path, first)
    add_vbts_record(csv_path, second)

    backups = tuple(backup_directory_for(csv_path).glob("*.csv"))
    assert backups


def test_bozuk_arsiv_guvenli_hata_uretir(tmp_path: Path) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    registry = tmp_path / "vbts_kayitlari.csv"
    registry.write_text("bozuk,sutun\n1,2\n", encoding="utf-8")

    with pytest.raises(DashboardVbtsManagerError):
        synchronize_vbts_operational_state(csv_path)


def test_operasyonel_durum_son_islemi_gosterir(tmp_path: Path) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    add_vbts_record(
        csv_path,
        _record("THYAO", "2026-07-01", "2026-07-31", "KAP-1"),
    )
    lifecycle = synchronize_vbts_operational_state(
        csv_path,
        date(2026, 7, 29),
    )

    status = read_operational_status(csv_path, lifecycle)

    assert status.synchronized_at != "—"
    assert status.last_action == "KAYIT_EKLENDI"
