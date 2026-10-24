from __future__ import annotations

from datetime import date
from pathlib import Path

from backend.app.compliance.dashboard_vbts_manager import (
    STATUS_ACTIVE,
    STATUS_EXPIRED,
    STATUS_FUTURE,
    add_vbts_record,
    build_vbts_record,
    classify_vbts_records,
    list_vbts_records,
    purge_expired_vbts_records,
    registry_path_for,
    sync_active_vbts_csv,
)


TODAY = date(2026, 7, 29)


def _record(symbol: str, start: str, end: str, ref: str):
    return build_vbts_record(
        symbol=symbol,
        measure_type="Tedbir",
        start_date=start,
        end_date=end,
        source_reference=ref,
    )


def test_kayit_durumlari_tarihe_gore_hesaplanir() -> None:
    active = _record("THYAO", "2026-07-01", "2026-07-29", "1")
    future = _record("ASELS", "2026-07-30", "2026-08-30", "2")
    expired = _record("TUPRS", "2026-06-01", "2026-07-28", "3")

    assert active.status(TODAY) == STATUS_ACTIVE
    assert future.status(TODAY) == STATUS_FUTURE
    assert expired.status(TODAY) == STATUS_EXPIRED


def test_yasam_dongusu_uc_gruba_ayrilir() -> None:
    records = (
        _record("THYAO", "2026-07-01", "2026-07-29", "1"),
        _record("ASELS", "2026-07-30", "2026-08-30", "2"),
        _record("TUPRS", "2026-06-01", "2026-07-28", "3"),
    )

    result = classify_vbts_records(records, TODAY)

    assert len(result.active) == 1
    assert len(result.future) == 1
    assert len(result.expired) == 1


def test_guncel_csvye_yalnizca_aktif_kayit_yazilir(tmp_path: Path) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    records = (
        _record("THYAO", "2026-07-01", "2026-07-29", "1"),
        _record("ASELS", "2026-07-30", "2026-08-30", "2"),
        _record("TUPRS", "2026-06-01", "2026-07-28", "3"),
    )

    sync_active_vbts_csv(csv_path, records, TODAY)

    text = csv_path.read_text(encoding="utf-8-sig")
    assert "THYAO" in text
    assert "ASELS" not in text
    assert "TUPRS" not in text


def test_arsiv_tum_kayitlari_korur(tmp_path: Path) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    records = (
        _record("THYAO", "2026-07-01", "2026-07-29", "1"),
        _record("ASELS", "2026-07-30", "2026-08-30", "2"),
    )

    for record in records:
        add_vbts_record(csv_path, record)

    assert len(list_vbts_records(csv_path)) == 2
    assert registry_path_for(csv_path).exists()


def test_aktif_kayit_yoksa_guncel_csv_kaldirilir(tmp_path: Path) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    future = _record("ASELS", "2026-07-30", "2026-08-30", "2")

    sync_active_vbts_csv(csv_path, (future,), TODAY)

    assert not csv_path.exists()


def test_suresi_dolmus_kayitlar_toplu_temizlenir(tmp_path: Path) -> None:
    csv_path = tmp_path / "vbts_guncel.csv"
    active = _record("THYAO", "2026-07-01", "2026-07-29", "1")
    expired = _record("TUPRS", "2026-06-01", "2026-07-28", "3")
    for record in (active, expired):
        add_vbts_record(csv_path, record)

    remaining = purge_expired_vbts_records(csv_path, TODAY)

    assert remaining == (active,)
    assert list_vbts_records(csv_path) == (active,)


def test_gosterim_satirinda_durum_sutunu_vardir() -> None:
    record = _record("THYAO", "2026-07-01", "2026-07-29", "1")

    assert record.as_display_row(TODAY)["Durum"] == STATUS_ACTIVE
