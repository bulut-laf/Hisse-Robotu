from __future__ import annotations

import io
import json
import zipfile
from datetime import date

import pytest

from backend.app.data.bist_official_archive import (
    archive_official_daily_snapshot,
    load_canonical_daily_snapshot,
)
from backend.app.data.bist_official_daily import official_daily_data_get


HEADER = (
    "TARIH;ISLEM  KODU;BULTEN ADI;ENSTRUMAN GRUBU;"
    "ACILIS FIYATI;EN YUKSEK FIYAT;EN DUSUK FIYAT;"
    "KAPANIS FIYATI;TOPLAM ISLEM ADEDI\n"
)


def _row(
    code: str,
    open_: str,
    high: str,
    low: str,
    close: str,
    volume: str,
) -> str:
    return (
        f"2026-08-03;{code};TEST;EQT;"
        f"{open_};{high};{low};{close};{volume}\n"
    )


def _zip(csv_text: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("thb202608031.csv", csv_text.encode("utf-8-sig"))
    return buffer.getvalue()


@pytest.fixture
def payload():
    return _zip(
        HEADER
        + _row("THYAO.E", "320.5", "322.25", "316.5", "317", "46594813")
        + _row("ASELS.E", "344", "346", "331.75", "336.25", "30271176")
    )


def test_official_provider_can_fetch_all_symbols_with_none(payload):
    def fetcher(url: str) -> bytes:
        return payload

    result = official_daily_data_get(
        None,
        date(2026, 8, 3),
        fetcher=fetcher,
        suffix_candidates=("1",),
    )
    assert set(result.veriler) == {"THYAO.IS", "ASELS.IS"}
    assert result.bulunamayan_semboller == ()


def test_archive_writes_raw_canonical_and_manifest(tmp_path, payload):
    def fetcher(url: str) -> bytes:
        return payload

    result = archive_official_daily_snapshot(
        date(2026, 8, 3),
        archive_root=tmp_path,
        symbols=None,
        fetcher=fetcher,
        suffix_candidates=("1",),
    )

    assert result.sembol_sayisi == 2
    assert result.raw_zip.exists()
    assert result.canonical_csv.exists()
    assert result.manifest_json.exists()


def test_canonical_csv_is_symbol_sorted(tmp_path, payload):
    def fetcher(url: str) -> bytes:
        return payload

    result = archive_official_daily_snapshot(
        date(2026, 8, 3),
        archive_root=tmp_path,
        symbols=None,
        fetcher=fetcher,
        suffix_candidates=("1",),
    )

    lines = result.canonical_csv.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "Date,Symbol,Open,High,Low,Close,Volume"
    assert lines[1].split(",")[1] == "ASELS.IS"
    assert lines[2].split(",")[1] == "THYAO.IS"


def test_manifest_has_required_metadata(tmp_path, payload):
    def fetcher(url: str) -> bytes:
        return payload

    result = archive_official_daily_snapshot(
        date(2026, 8, 3),
        archive_root=tmp_path,
        fetcher=fetcher,
        suffix_candidates=("1",),
    )

    manifest = json.loads(result.manifest_json.read_text(encoding="utf-8"))
    assert manifest["source"] == "Borsa Istanbul Official Daily Bulletin"
    assert manifest["trade_date"] == "2026-08-03"
    assert manifest["symbol_count"] == 2
    assert len(manifest["canonical_sha256"]) == 64


def test_loader_reconstructs_symbol_frames(tmp_path, payload):
    def fetcher(url: str) -> bytes:
        return payload

    archive_official_daily_snapshot(
        date(2026, 8, 3),
        archive_root=tmp_path,
        fetcher=fetcher,
        suffix_candidates=("1",),
    )

    data = load_canonical_daily_snapshot(
        date(2026, 8, 3),
        archive_root=tmp_path,
    )

    assert set(data) == {"ASELS.IS", "THYAO.IS"}
    assert data["THYAO.IS"].iloc[-1]["High"] == pytest.approx(322.25)
    assert data["THYAO.IS"].iloc[-1]["Volume"] == pytest.approx(46594813)


def test_same_snapshot_is_idempotent(tmp_path, payload):
    def fetcher(url: str) -> bytes:
        return payload

    first = archive_official_daily_snapshot(
        date(2026, 8, 3),
        archive_root=tmp_path,
        fetcher=fetcher,
        suffix_candidates=("1",),
    )
    second = archive_official_daily_snapshot(
        date(2026, 8, 3),
        archive_root=tmp_path,
        fetcher=fetcher,
        suffix_candidates=("1",),
    )

    assert first.sha256 == second.sha256
    assert first.canonical_csv.read_bytes() == second.canonical_csv.read_bytes()


def test_conflicting_verified_snapshot_is_not_overwritten(tmp_path, payload):
    def fetcher1(url: str) -> bytes:
        return payload

    archive_official_daily_snapshot(
        date(2026, 8, 3),
        archive_root=tmp_path,
        fetcher=fetcher1,
        suffix_candidates=("1",),
    )

    changed = _zip(
        HEADER
        + _row("THYAO.E", "320.5", "322.25", "316.5", "318", "46594813")
        + _row("ASELS.E", "344", "346", "331.75", "336.25", "30271176")
    )

    def fetcher2(url: str) -> bytes:
        return changed

    with pytest.raises(RuntimeError, match="üzerine yazma engellendi"):
        archive_official_daily_snapshot(
            date(2026, 8, 3),
            archive_root=tmp_path,
            fetcher=fetcher2,
            suffix_candidates=("1",),
        )


def test_requested_subset_is_archived_as_subset(tmp_path, payload):
    def fetcher(url: str) -> bytes:
        return payload

    result = archive_official_daily_snapshot(
        date(2026, 8, 3),
        archive_root=tmp_path,
        symbols=["THYAO.IS"],
        fetcher=fetcher,
        suffix_candidates=("1",),
    )
    assert result.sembol_sayisi == 1

    data = load_canonical_daily_snapshot(
        date(2026, 8, 3),
        archive_root=tmp_path,
    )
    assert set(data) == {"THYAO.IS"}
