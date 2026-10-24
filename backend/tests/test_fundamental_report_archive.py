from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from backend.app.reporting.fundamental_report import FundamentalReport
from backend.app.reporting.fundamental_report_archive import (
    FundamentalReportArchiveError,
    FundamentalReportJsonArchive,
    compare_archived_reports,
    report_archive_rows,
    report_comparison_rows,
)


def report(
    *,
    symbol="AAA",
    period_key="2026Q2",
    period_end=date(2026, 6, 30),
    total_score=76,
    source="manual.csv",
    current_ratio="2.00",
):
    return FundamentalReport(
        symbol=symbol,
        period_key=period_key,
        period_end=period_end,
        currency="TRY",
        source=source,
        freshness_status="Güncel",
        age_days=31,
        total_score=total_score,
        grade="İyi",
        component_scores=(
            ("Kârlılık", 15, 25),
            ("Büyüme", 20, 25),
            ("Borçluluk", 12, 20),
            ("Likidite", 14, 15),
            ("Nakit akışı", 15, 15),
        ),
        score_change="+5",
        ratio_rows=(("Cari oran", current_ratio),),
        sector_ratio_rows=(),
        sector_ranking="2/5",
        sector_strength="Güçleniyor",
        quality_flags=(),
        generated_at=datetime.now(timezone.utc),
    )


def test_rapor_arsive_kaydedilir(tmp_path):
    archive = FundamentalReportJsonArchive(
        tmp_path / "reports.json"
    )

    result = archive.save(report())

    assert result.inserted == 1
    assert result.unchanged == 0
    assert result.archived.symbol == "AAA"


def test_ayni_veri_kimligi_mukerrer_kaydedilmez(tmp_path):
    archive = FundamentalReportJsonArchive(
        tmp_path / "reports.json"
    )
    first = report()
    second = report()

    archive.save(first)
    result = archive.save(second)

    assert result.inserted == 0
    assert result.unchanged == 1
    assert len(archive.list_symbol("AAA")) == 1


def test_yeni_finansal_veri_yeni_surum_olusturur(tmp_path):
    archive = FundamentalReportJsonArchive(
        tmp_path / "reports.json"
    )

    archive.save(report(total_score=70))
    archive.save(report(total_score=76))

    assert len(archive.list_symbol("AAA")) == 2


def test_sirket_raporlari_yeniden_eskiye_listelenir(tmp_path):
    archive = FundamentalReportJsonArchive(
        tmp_path / "reports.json"
    )
    archive.save(
        report(
            period_key="2026Q1",
            period_end=date(2026, 3, 31),
        )
    )
    archive.save(report())

    items = archive.list_symbol(
        "AAA",
        today=date(2026, 7, 31),
    )

    assert tuple(item.period_key for item in items) == (
        "2026Q2",
        "2026Q1",
    )


def test_eski_rapor_guvenli_bicimde_dislanir(tmp_path):
    archive = FundamentalReportJsonArchive(
        tmp_path / "reports.json"
    )
    archive.save(
        report(
            period_key="2023Q4",
            period_end=date(2023, 12, 31),
        )
    )

    items = archive.list_symbol(
        "AAA",
        today=date(2026, 7, 31),
        maximum_age_days=365,
    )

    assert items == ()


def test_gecmis_raporlar_karsilastirilir(tmp_path):
    archive = FundamentalReportJsonArchive(
        tmp_path / "reports.json"
    )
    previous = archive.save(
        report(
            period_key="2026Q1",
            period_end=date(2026, 3, 31),
            total_score=70,
            current_ratio="1.50",
        )
    ).archived
    current = archive.save(
        report(
            total_score=76,
            current_ratio="2.00",
        )
    ).archived

    comparison = compare_archived_reports(previous, current)

    assert comparison.total_score_change == 6
    assert comparison.ratio_changes == (
        ("Cari oran", "1.50", "2.00"),
    )
    assert report_comparison_rows(comparison)[0]["Değişim"] == 6


def test_farkli_sirket_raporlari_karsilastirilamaz(tmp_path):
    archive = FundamentalReportJsonArchive(
        tmp_path / "reports.json"
    )
    first = archive.save(report(symbol="AAA")).archived
    second = archive.save(report(symbol="BBB")).archived

    with pytest.raises(
        FundamentalReportArchiveError,
        match="aynı şirkete",
    ):
        compare_archived_reports(first, second)


def test_arsiv_tablo_satirlari_uretilir(tmp_path):
    archive = FundamentalReportJsonArchive(
        tmp_path / "reports.json"
    )
    archived = archive.save(report()).archived

    rows = report_archive_rows((archived,))

    assert rows[0]["Rapor kimliği"] == archived.report_id
    assert rows[0]["Temel skor"] == 76
