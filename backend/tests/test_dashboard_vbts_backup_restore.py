from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from backend.app.compliance.dashboard_vbts_manager import (
    DashboardVbtsManagerError,
    add_vbts_record,
    audit_display_rows,
    backup_directory_for,
    build_vbts_record,
    delete_vbts_record,
    inspect_vbts_backup,
    list_vbts_backups,
    list_vbts_records,
    read_audit_events,
    restore_vbts_backup,
)


def _record(symbol: str, ref: str):
    return build_vbts_record(
        symbol=symbol,
        measure_type="Tedbir",
        start_date="2026-07-01",
        end_date="2026-08-31",
        source_reference=ref,
    )


def _create_registry_backup(csv_path: Path) -> Path:
    first = _record("THYAO", "KAP-1")
    second = _record("ASELS", "KAP-2")
    add_vbts_record(csv_path, first)
    add_vbts_record(csv_path, second)
    delete_vbts_record(csv_path, second.record_key)
    backups = list_vbts_backups(csv_path)
    assert backups
    return next(item.path for item in backups if item.record_count == 2)


def test_yedekler_yeniden_eskiye_listelenir(tmp_path: Path) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    _create_registry_backup(csv_path)

    backups = list_vbts_backups(csv_path)

    assert backups
    assert all(item.file_name.startswith("vbts_kayitlari_") for item in backups)


def test_yedek_geri_yuklemeden_once_dogrulanir(tmp_path: Path) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    backup_path = _create_registry_backup(csv_path)

    records, lifecycle = inspect_vbts_backup(
        csv_path,
        backup_path,
        date(2026, 7, 29),
    )

    assert len(records) == 2
    assert len(lifecycle.active) == 2


def test_yedek_klasoru_disindaki_dosya_reddedilir(tmp_path: Path) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    outside = tmp_path / "outside.csv"
    outside.write_text(
        "symbol,measure_type,start_date,end_date,source_reference\n"
        "THYAO,Tedbir,2026-07-01,2026-08-31,KAP-1\n",
        encoding="utf-8",
    )

    with pytest.raises(DashboardVbtsManagerError):
        inspect_vbts_backup(csv_path, outside)


def test_bozuk_yedek_reddedilir(tmp_path: Path) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    backup_dir = backup_directory_for(csv_path)
    backup_dir.mkdir(parents=True)
    broken = backup_dir / "vbts_kayitlari_bozuk.csv"
    broken.write_text("bozuk,sutun\n1,2\n", encoding="utf-8")

    with pytest.raises(DashboardVbtsManagerError):
        inspect_vbts_backup(csv_path, broken)


def test_yedek_geri_yukleme_arsivi_ve_aktif_csvyi_senkronize_eder(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    backup_path = _create_registry_backup(csv_path)

    restored = restore_vbts_backup(
        csv_path,
        backup_path,
        date(2026, 7, 29),
    )

    assert len(restored) == 2
    assert len(list_vbts_records(csv_path)) == 2
    assert "ASELS" in csv_path.read_text(encoding="utf-8-sig")


def test_geri_yukleme_denetim_gunlugune_yazilir(tmp_path: Path) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    backup_path = _create_registry_backup(csv_path)

    restore_vbts_backup(csv_path, backup_path)

    events = read_audit_events(csv_path, limit=50)
    assert events[0]["action"] == "YEDEK_GERI_YUKLENDI"


def test_denetim_olaylari_son_islem_ilk_sirada_doner(tmp_path: Path) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    first = _record("THYAO", "KAP-1")
    add_vbts_record(csv_path, first)
    delete_vbts_record(csv_path, first.record_key)

    events = read_audit_events(csv_path, limit=10)

    assert events[0]["action"] == "KAYIT_SILINDI"
    assert events[1]["action"] == "KAYIT_EKLENDI"


def test_denetim_gosterim_satirlari_turkce_sutunlar_uretir(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    add_vbts_record(csv_path, _record("THYAO", "KAP-1"))

    rows = audit_display_rows(read_audit_events(csv_path))

    assert rows[0]["İşlem"] == "KAYIT_EKLENDI"
    assert "Zaman (UTC)" in rows[0]
