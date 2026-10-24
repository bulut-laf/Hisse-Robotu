from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.compliance.dashboard_vbts_manager import (
    DashboardVbtsManagerError,
    add_vbts_record,
    audit_events_csv_bytes,
    backup_directory_for,
    backup_manifest_path_for,
    build_vbts_record,
    delete_vbts_record,
    inspect_vbts_backup,
    list_vbts_backups,
    prune_vbts_backups,
    validate_vbts_system_health,
    verify_backup_integrity,
)


def _record(symbol: str, ref: str):
    return build_vbts_record(
        symbol=symbol,
        measure_type="Tedbir",
        start_date="2026-07-01",
        end_date="2026-08-31",
        source_reference=ref,
    )


def _make_backup(csv_path: Path) -> Path:
    first = _record("THYAO", "KAP-1")
    second = _record("ASELS", "KAP-2")
    add_vbts_record(csv_path, first)
    add_vbts_record(csv_path, second)
    delete_vbts_record(csv_path, second.record_key)
    return list_vbts_backups(csv_path)[0].path


def test_yedek_manifesti_ve_sha256_olusturulur(tmp_path: Path) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    backup = _make_backup(csv_path)

    assert backup_manifest_path_for(csv_path).exists()
    assert verify_backup_integrity(csv_path, backup)


def test_degistirilmis_yedek_reddedilir(tmp_path: Path) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    backup = _make_backup(csv_path)
    backup.write_text("degistirildi", encoding="utf-8")

    with pytest.raises(DashboardVbtsManagerError):
        inspect_vbts_backup(csv_path, backup)


def test_manifestte_olmayan_yedek_reddedilir(tmp_path: Path) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    backup_dir = backup_directory_for(csv_path)
    backup_dir.mkdir(parents=True)
    rogue = backup_dir / "vbts_kayitlari_rogue.csv"
    rogue.write_text(
        "symbol,measure_type,start_date,end_date,source_reference\n"
        "THYAO,Tedbir,2026-07-01,2026-08-31,KAP-1\n",
        encoding="utf-8",
    )

    with pytest.raises(DashboardVbtsManagerError):
        verify_backup_integrity(csv_path, rogue)


def test_yedek_saklama_politikasi_eski_yedekleri_temizler(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    _make_backup(csv_path)
    add_vbts_record(csv_path, _record("TUPRS", "KAP-3"))
    backups_before = tuple(backup_directory_for(csv_path).glob("*.csv"))

    removed = prune_vbts_backups(csv_path, keep_latest=1)

    assert len(removed) == max(0, len(backups_before) - 1)
    assert len(tuple(backup_directory_for(csv_path).glob("*.csv"))) == 1


def test_denetim_gunlugu_csv_baytlari_uretilir() -> None:
    data = audit_events_csv_bytes(
        (
            {
                "timestamp_utc": "2026-07-29T10:00:00+00:00",
                "action": "KAYIT_EKLENDI",
                "detail": "Test",
                "record_key": "abc",
            },
        )
    )

    text = data.decode("utf-8-sig")
    assert "timestamp_utc,action,detail,record_key" in text
    assert "KAYIT_EKLENDI" in text


def test_sistem_sagligi_saglikli_dosyalarla_olumludur(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    add_vbts_record(csv_path, _record("THYAO", "KAP-1"))

    report = validate_vbts_system_health(csv_path)

    assert report.healthy
    assert "Sağlıklı" in report.registry_status
    assert "Sağlıklı" in report.active_csv_status


def test_sistem_sagligi_degistirilmis_yedekte_sorunludur(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    backup = _make_backup(csv_path)
    backup.write_text("degistirildi", encoding="utf-8")

    report = validate_vbts_system_health(csv_path)

    assert not report.healthy
    assert report.backup_status == "Bütünlük hatası"
