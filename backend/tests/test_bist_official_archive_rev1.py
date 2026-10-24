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
from backend.app.data.bist_official_daily import (
    BistOfficialDailyError,
    official_daily_data_get,
    parse_bulletin_zip,
)


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


def test_strict_parser_still_rejects_invalid_ohlc():
    invalid = _zip(
        HEADER
        + _row("THYAO.E", "320.5", "322.25", "316.5", "317", "46594813")
        + _row("UMPAS.E", "0", "0", "0", "0", "0")
    )
    with pytest.raises(BistOfficialDailyError, match="UMPAS"):
        parse_bulletin_zip(invalid, date(2026, 8, 3))


def test_bulk_provider_can_skip_invalid_and_report_it():
    payload = _zip(
        HEADER
        + _row("THYAO.E", "320.5", "322.25", "316.5", "317", "46594813")
        + _row("UMPAS.E", "0", "0", "0", "0", "0")
    )

    def fetcher(url: str) -> bytes:
        return payload

    result = official_daily_data_get(
        None,
        date(2026, 8, 3),
        fetcher=fetcher,
        suffix_candidates=("1",),
        skip_invalid=True,
    )

    assert set(result.veriler) == {"THYAO.IS"}
    assert result.gecersiz_semboller == ("UMPAS.IS",)


def test_invalid_requested_symbol_is_missing_and_invalid():
    payload = _zip(
        HEADER
        + _row("THYAO.E", "320.5", "322.25", "316.5", "317", "46594813")
        + _row("UMPAS.E", "0", "0", "0", "0", "0")
    )

    def fetcher(url: str) -> bytes:
        return payload

    result = official_daily_data_get(
        ["THYAO.IS", "UMPAS.IS"],
        date(2026, 8, 3),
        fetcher=fetcher,
        suffix_candidates=("1",),
        skip_invalid=True,
    )

    assert set(result.veriler) == {"THYAO.IS"}
    assert result.bulunamayan_semboller == ("UMPAS.IS",)
    assert result.gecersiz_semboller == ("UMPAS.IS",)


def test_archive_excludes_invalid_and_records_manifest(tmp_path):
    payload = _zip(
        HEADER
        + _row("THYAO.E", "320.5", "322.25", "316.5", "317", "46594813")
        + _row("ASELS.E", "344", "346", "331.75", "336.25", "30271176")
        + _row("UMPAS.E", "0", "0", "0", "0", "0")
    )

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
    assert result.gecersiz_semboller == ("UMPAS.IS",)

    data = load_canonical_daily_snapshot(
        date(2026, 8, 3),
        archive_root=tmp_path,
    )
    assert set(data) == {"ASELS.IS", "THYAO.IS"}

    manifest = json.loads(result.manifest_json.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 2
    assert manifest["invalid_excluded_symbols"] == ["UMPAS.IS"]


def test_existing_valid_archive_behavior_still_works(tmp_path, payload):
    def fetcher(url: str) -> bytes:
        return payload

    result = archive_official_daily_snapshot(
        date(2026, 8, 3),
        archive_root=tmp_path,
        fetcher=fetcher,
        suffix_candidates=("1",),
    )

    assert result.sembol_sayisi == 2
    assert result.gecersiz_semboller == ()
    assert result.raw_zip.exists()
    assert result.canonical_csv.exists()
    assert result.manifest_json.exists()
