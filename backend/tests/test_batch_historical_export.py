from datetime import date
from pathlib import Path
import csv
import io
import zipfile

import pytest

from backend.app.history.batch_historical_export import (
    BatchReplayRequest,
    default_combined_filename,
    default_zip_filename,
    iter_cut_dates,
    rows_to_csv_text,
    run_batch_replay,
    write_combined_csv,
    write_daily_zip,
)


def test_tarih_araligi_hafta_ici():
    req = BatchReplayRequest(
        start_date=date(2026, 6, 29),
        end_date=date(2026, 7, 3),
    )
    assert iter_cut_dates(req) == (
        date(2026, 6, 29),
        date(2026, 6, 30),
        date(2026, 7, 1),
        date(2026, 7, 2),
        date(2026, 7, 3),
    )


def test_hafta_sonu_atlanir():
    req = BatchReplayRequest(
        start_date=date(2026, 7, 3),
        end_date=date(2026, 7, 6),
    )
    assert iter_cut_dates(req) == (
        date(2026, 7, 3),
        date(2026, 7, 6),
    )


def test_hafta_sonu_dahil_edilebilir():
    req = BatchReplayRequest(
        start_date=date(2026, 7, 3),
        end_date=date(2026, 7, 5),
        weekdays_only=False,
    )
    assert len(iter_cut_dates(req)) == 3


def test_batch_tarama_kesim_tarihini_ekler():
    def scan_day(cut_date, universe):
        return [{"Hisse": "TRMET", "Sıra": 20}]

    req = BatchReplayRequest(date(2026, 7, 1), date(2026, 7, 2), "BIST100")
    result = run_batch_replay(req, scan_day=scan_day)

    assert result.processed_days == 2
    assert result.total_rows == 2
    assert result.combined_rows[0]["Kesim Tarihi"] == "2026-07-01"
    assert result.combined_rows[0]["Evren"] == "BIST100"


def test_batch_tarama_evreni_scannera_gonderir():
    calls = []

    def scan_day(cut_date, universe):
        calls.append((cut_date, universe))
        return []

    req = BatchReplayRequest(date(2026, 7, 1), date(2026, 7, 1), "BISTTUM")
    run_batch_replay(req, scan_day=scan_day)

    assert calls == [(date(2026, 7, 1), "BISTTUM")]


def test_bos_gunler_de_sonuca_girer():
    def scan_day(cut_date, universe):
        return []

    req = BatchReplayRequest(date(2026, 7, 1), date(2026, 7, 2))
    result = run_batch_replay(req, scan_day=scan_day)

    assert result.processed_days == 2
    assert result.total_rows == 0
    assert result.days[0].row_count == 0


def test_csv_kesim_tarihi_ve_evren_basta():
    text = rows_to_csv_text([
        {"Hisse": "AAA", "Sıra": 1, "Kesim Tarihi": "2026-07-01", "Evren": "BIST100"}
    ])
    header = text.splitlines()[0]
    assert header.startswith("Kesim Tarihi,Evren,")


def test_csv_turkce_alanlari_korur():
    text = rows_to_csv_text([
        {
            "Kesim Tarihi": "2026-07-01",
            "Evren": "BIST100",
            "Hisse": "EFOR",
            "Kesim sınıfı": "E1",
            "Dirence uzaklık (%)": 5.5,
        }
    ])
    assert "Kesim sınıfı" in text
    assert "Dirence uzaklık (%)" in text


def test_combined_csv_yazilir(tmp_path):
    def scan_day(cut_date, universe):
        return [{"Hisse": "AAA", "Sıra": 1}]

    req = BatchReplayRequest(date(2026, 7, 1), date(2026, 7, 1))
    result = run_batch_replay(req, scan_day=scan_day)
    path = write_combined_csv(result, tmp_path / "all.csv")

    assert path.exists()
    content = path.read_text(encoding="utf-8-sig")
    assert "AAA" in content
    assert "2026-07-01" in content


def test_daily_zip_her_gun_icin_csv_uretir(tmp_path):
    def scan_day(cut_date, universe):
        return [{"Hisse": "AAA"}]

    req = BatchReplayRequest(date(2026, 7, 1), date(2026, 7, 2), "BIST100")
    result = run_batch_replay(req, scan_day=scan_day)
    path = write_daily_zip(result, tmp_path / "daily.zip")

    with zipfile.ZipFile(path) as zf:
        names = sorted(zf.namelist())

    assert names == [
        "2026-07-01_BIST100.csv",
        "2026-07-02_BIST100.csv",
    ]


def test_default_dosya_adlari():
    req = BatchReplayRequest(date(2026, 6, 29), date(2026, 7, 29), "BIST100")
    assert default_combined_filename(req) == (
        "tarihsel_toplu_BIST100_2026-06-29_2026-07-29.csv"
    )
    assert default_zip_filename(req) == (
        "tarihsel_gunluk_BIST100_2026-06-29_2026-07-29.zip"
    )


def test_gecersiz_tarih_araligi():
    with pytest.raises(ValueError):
        BatchReplayRequest(date(2026, 7, 2), date(2026, 7, 1))


def test_bos_evren_reddedilir():
    with pytest.raises(ValueError):
        BatchReplayRequest(date(2026, 7, 1), date(2026, 7, 1), " ")


def test_tek_gun_calisir():
    req = BatchReplayRequest(date(2026, 7, 1), date(2026, 7, 1))
    assert iter_cut_dates(req) == (date(2026, 7, 1),)


def test_bos_csv_sadece_baslik():
    assert rows_to_csv_text([]) == "Kesim Tarihi,Evren\r\n"
