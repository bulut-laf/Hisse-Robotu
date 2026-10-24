
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from backend.app.compliance import dashboard_vbts_manager as manager


def _record() -> manager.DashboardVbtsRecord:
    return manager.build_vbts_record(
        symbol="THYAO",
        measure_type="Açığa satış ve kredili işlem yasağı",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
        source_reference="KAP-2026-001",
    )


def test_automatic_sync_does_not_create_redundant_backup(tmp_path: Path) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    manager.add_vbts_record(csv_path, _record())
    backup_dir = manager.backup_directory_for(csv_path)

    before = tuple(backup_dir.glob("*.csv")) if backup_dir.exists() else ()
    manager.synchronize_vbts_operational_state(
        csv_path,
        on_date=date(2026, 7, 15),
    )
    after_first = tuple(backup_dir.glob("*.csv")) if backup_dir.exists() else ()
    manager.synchronize_vbts_operational_state(
        csv_path,
        on_date=date(2026, 7, 15),
    )
    after_second = tuple(backup_dir.glob("*.csv")) if backup_dir.exists() else ()

    assert len(after_first) == len(before)
    assert len(after_second) == len(after_first)


def test_sync_state_uses_requested_control_date(tmp_path: Path) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    manager.add_vbts_record(csv_path, _record())

    manager.synchronize_vbts_operational_state(
        csv_path,
        on_date=date(2026, 7, 15),
    )

    state_path = manager.synchronization_state_path_for(csv_path)
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    assert payload["synchronized_for_date"] == "2026-07-15"


def test_backup_names_are_unique_inside_same_second(tmp_path: Path) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    csv_path.write_text(
        "symbol,measure_type,start_date,end_date,source_reference\n"
        "THYAO,Açığa satış yasağı,2026-07-01,2026-07-31,KAP-2026-001\n",
        encoding="utf-8-sig",
    )

    first = manager._create_backup(csv_path, "test")
    second = manager._create_backup(csv_path, "test")

    assert first is not None
    assert second is not None
    assert first != second
    assert first.exists()
    assert second.exists()


def test_legacy_backup_is_parsed_before_manifest_registration(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    backup_dir = manager.backup_directory_for(csv_path)
    backup_dir.mkdir(parents=True)
    broken = backup_dir / "vbts_kayitlari_legacy.csv"
    broken.write_text("bozuk,sutunlar\n1,2\n", encoding="utf-8")

    try:
        manager.migrate_existing_backups_to_manifest(csv_path)
    except manager.DashboardVbtsManagerError:
        pass
    else:
        raise AssertionError("Bozuk yedek manifestte güvenilir kabul edilmemeliydi.")

    manifest_path = manager.backup_manifest_path_for(csv_path)
    if manifest_path.exists():
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert broken.name not in payload
