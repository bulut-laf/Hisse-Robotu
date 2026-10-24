from __future__ import annotations

import ast
from pathlib import Path


DASHBOARD = Path("backend/dashboard.py")


def source() -> str:
    return DASHBOARD.read_text(encoding="utf-8")


def test_temel_rapor_yerel_arsive_kaydedilir():
    text = source()

    assert "Temel analiz rapor arşivi" in text
    assert "FundamentalReportJsonArchive" in text
    assert "rapor_arsivi.save" in text
    assert "report_archive_rows" in text


def test_mukerrer_rapor_durumu_gosterilir():
    text = source()

    assert "eklenen" in text
    assert "değişmeyen" in text


def test_gecmis_raporlar_karsilastirilir():
    text = source()

    assert "Önceki temel rapor" in text
    assert "Güncel temel rapor" in text
    assert "compare_archived_reports" in text
    assert "report_comparison_rows" in text


def test_arsiv_karsilastirmasi_sinyal_uretmez():
    text = source()

    assert "Alım/satım tavsiyesi" in text
    assert "üretmez" in text


def test_dashboard_sozdizimi_gecerlidir():
    ast.parse(source())
