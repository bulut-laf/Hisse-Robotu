from __future__ import annotations

import io
import zipfile
from datetime import date

import pandas as pd
import pytest

from backend.app.data.bist_official_daily import (
    BistOfficialDailyError,
    bulletin_filename,
    bulletin_url,
    download_bulletin_zip,
    normalize_symbol,
    official_daily_data_get,
    parse_bulletin_zip,
    yahoo_style_symbol,
)


HEADER = (
    "TARIH;ISLEM  KODU;BULTEN ADI;ENSTRUMAN GRUBU;"
    "ACILIS FIYATI;EN YUKSEK FIYAT;EN DUSUK FIYAT;"
    "KAPANIS FIYATI;TOPLAM ISLEM ADEDI\n"
)


def _zip(csv_text: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("thb202608031.csv", csv_text.encode("utf-8-sig"))
    return buffer.getvalue()


def _row(
    code="THYAO.E",
    group="EQT",
    open_="320.5",
    high="322.25",
    low="316.5",
    close="317",
    volume="46594813",
):
    return (
        f"2026-08-03;{code};TEST;{group};"
        f"{open_};{high};{low};{close};{volume}\n"
    )


def test_symbol_normalization():
    assert normalize_symbol("thyao") == "THYAO"
    assert normalize_symbol("THYAO.IS") == "THYAO"
    assert normalize_symbol("THYAO.E") == "THYAO"
    assert yahoo_style_symbol("thyao") == "THYAO.IS"


def test_bulletin_filename_and_url():
    d = date(2026, 8, 3)
    assert bulletin_filename(d, "1") == "thb202608031.zip"
    assert bulletin_url(d, "1").endswith(
        "/data/thb/2026/08/thb202608031.zip"
    )


def test_parse_single_thyao_full_ohlcv():
    payload = _zip(HEADER + _row())
    data, missing = parse_bulletin_zip(
        payload,
        date(2026, 8, 3),
        symbols=["THYAO.IS"],
    )
    assert missing == ()
    df = data["THYAO.IS"]
    assert list(df.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert df.index[-1] == pd.Timestamp("2026-08-03")
    assert df.iloc[-1]["Open"] == pytest.approx(320.5)
    assert df.iloc[-1]["High"] == pytest.approx(322.25)
    assert df.iloc[-1]["Low"] == pytest.approx(316.5)
    assert df.iloc[-1]["Close"] == pytest.approx(317)
    assert df.iloc[-1]["Volume"] == pytest.approx(46594813)


def test_ignores_non_equity_and_non_e_rows():
    payload = _zip(
        HEADER
        + _row(code="THYAO.AOF", group="AOF")
        + _row(code="TBIPE.V", group="EPW")
        + _row(code="THYAO.E", group="EQT")
    )
    data, _ = parse_bulletin_zip(payload, date(2026, 8, 3))
    assert set(data) == {"THYAO.IS"}


def test_requested_missing_symbol_is_reported():
    payload = _zip(HEADER + _row())
    data, missing = parse_bulletin_zip(
        payload,
        date(2026, 8, 3),
        symbols=["THYAO.IS", "ASELS.IS"],
    )
    assert set(data) == {"THYAO.IS"}
    assert missing == ("ASELS.IS",)


def test_missing_high_is_rejected():
    payload = _zip(HEADER + _row(high=""))
    with pytest.raises(BistOfficialDailyError, match="eksik OHLCV"):
        parse_bulletin_zip(payload, date(2026, 8, 3))


def test_inconsistent_high_is_rejected():
    payload = _zip(HEADER + _row(high="310"))
    with pytest.raises(BistOfficialDailyError, match="HIGH"):
        parse_bulletin_zip(payload, date(2026, 8, 3))


def test_inconsistent_low_is_rejected():
    # LOW kuralını izole etmek için HIGH, LOW değerinden büyük tutulur.
    payload = _zip(HEADER + _row(high="330", low="325"))
    with pytest.raises(BistOfficialDailyError, match="LOW"):
        parse_bulletin_zip(payload, date(2026, 8, 3))


def test_duplicate_equity_symbol_is_rejected():
    payload = _zip(HEADER + _row() + _row())
    with pytest.raises(BistOfficialDailyError, match="birden fazla"):
        parse_bulletin_zip(payload, date(2026, 8, 3))


def test_download_tries_next_suffix_after_404():
    payload = _zip(HEADER + _row())
    calls = []

    def fetcher(url: str) -> bytes:
        calls.append(url)
        if url.endswith("1.zip"):
            raise RuntimeError("404")
        if url.endswith("2.zip"):
            return payload
        raise AssertionError(url)

    url, received = download_bulletin_zip(
        date(2026, 8, 3),
        fetcher=fetcher,
        suffix_candidates=("1", "2"),
    )
    assert url.endswith("thb202608032.zip")
    assert received == payload
    assert len(calls) == 2


def test_official_daily_data_get_archives_raw_zip(tmp_path):
    payload = _zip(HEADER + _row())

    def fetcher(url: str) -> bytes:
        assert url.endswith("thb202608031.zip")
        return payload

    result = official_daily_data_get(
        ["THYAO.IS"],
        date(2026, 8, 3),
        archive_root=tmp_path,
        fetcher=fetcher,
        suffix_candidates=("1",),
    )

    assert "THYAO.IS" in result.veriler
    assert result.bulunamayan_semboller == ()
    assert result.arsiv_dosyasi is not None
    assert result.arsiv_dosyasi.exists()
    assert result.arsiv_dosyasi.read_bytes() == payload


def test_wrong_date_rows_are_ignored():
    other = _row().replace("2026-08-03", "2026-07-31")
    payload = _zip(HEADER + other)
    data, missing = parse_bulletin_zip(
        payload,
        date(2026, 8, 3),
        symbols=["THYAO.IS"],
    )
    assert data == {}
    assert missing == ("THYAO.IS",)
