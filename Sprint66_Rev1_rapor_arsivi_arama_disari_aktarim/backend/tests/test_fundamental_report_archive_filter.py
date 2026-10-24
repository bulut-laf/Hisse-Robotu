from __future__ import annotations

from datetime import date

import pytest

from backend.app.reporting.fundamental_report_archive import (
    FundamentalReportArchiveError,
    FundamentalReportArchiveFilter,
    FundamentalReportJsonArchive,
    archived_reports_csv_bytes,
    archived_reports_pdf_bytes,
    search_archived_reports,
)
from backend.tests.test_fundamental_report_archive import report


def archived_reports(tmp_path):
    archive = FundamentalReportJsonArchive(
        tmp_path / "reports.json"
    )
    archive.save(
        report(
            symbol="AAA",
            period_key="2026Q1",
            period_end=date(2026, 3, 31),
            total_score=65,
            source="manual.csv",
        )
    )
    archive.save(
        report(
            symbol="AAA",
            period_key="2026Q2",
            period_end=date(2026, 6, 30),
            total_score=80,
            source="kap.json",
        )
    )
    archive.save(
        report(
            symbol="BBB",
            period_key="2026Q2",
            period_end=date(2026, 6, 30),
            total_score=55,
            source="manual.csv",
        )
    )
    return archive.list_all(today=date(2026, 7, 31))


def test_sembol_donem_ve_skor_filtreleri_uygulanir(tmp_path):
    items = archived_reports(tmp_path)

    result = search_archived_reports(
        items,
        FundamentalReportArchiveFilter(
            symbol_query="AAA",
            period_start=date(2026, 4, 1),
            period_end=date(2026, 7, 31),
            minimum_score=70,
            maximum_score=90,
        ),
    )

    assert len(result) == 1
    assert result[0].period_key == "2026Q2"
    assert result[0].report.total_score == 80


def test_kaynak_kalite_ve_tazelik_filtreleri_uygulanir(tmp_path):
    items = archived_reports(tmp_path)

    result = search_archived_reports(
        items,
        FundamentalReportArchiveFilter(
            grades=("İyi",),
            sources=("kap.json",),
            freshness_statuses=("Güncel",),
        ),
    )

    assert len(result) == 1
    assert result[0].symbol == "AAA"
    assert result[0].report.source == "kap.json"


@pytest.mark.parametrize(
    "sort_by",
    (
        "period_desc",
        "period_asc",
        "created_desc",
        "created_asc",
        "score_desc",
        "score_asc",
    ),
)
def test_desteklenen_siralama_secenekleri(sort_by, tmp_path):
    items = archived_reports(tmp_path)

    result = search_archived_reports(
        items,
        FundamentalReportArchiveFilter(sort_by=sort_by),
    )

    assert len(result) == 3


def test_skor_siralama_dogru_calısir(tmp_path):
    items = archived_reports(tmp_path)

    descending = search_archived_reports(
        items,
        FundamentalReportArchiveFilter(sort_by="score_desc"),
    )
    ascending = search_archived_reports(
        items,
        FundamentalReportArchiveFilter(sort_by="score_asc"),
    )

    assert descending[0].report.total_score == 80
    assert ascending[0].report.total_score == 55


def test_gecersiz_tarih_araligi_reddedilir():
    with pytest.raises(
        FundamentalReportArchiveError,
        match="başlangıcı",
    ):
        FundamentalReportArchiveFilter(
            period_start=date(2026, 7, 1),
            period_end=date(2026, 6, 1),
        )


def test_gecersiz_skor_araligi_reddedilir():
    with pytest.raises(
        FundamentalReportArchiveError,
        match="Asgari skor",
    ):
        FundamentalReportArchiveFilter(
            minimum_score=90,
            maximum_score=60,
        )


def test_filtrelenmis_arsiv_csv_uretilir(tmp_path):
    items = archived_reports(tmp_path)

    content = archived_reports_csv_bytes(items)

    assert content.startswith(b"\xef\xbb\xbf")
    assert b"report_id" in content
    assert b"AAA" in content


def test_secili_raporlar_toplu_pdf_uretir(tmp_path):
    items = archived_reports(tmp_path)

    content = archived_reports_pdf_bytes(items[:2])

    assert content.startswith(b"%PDF")
    assert len(content) > 1000


def test_bos_toplu_pdf_reddedilir():
    with pytest.raises(
        FundamentalReportArchiveError,
        match="en az bir rapor",
    ):
        archived_reports_pdf_bytes(())
