from __future__ import annotations

import ast
from pathlib import Path

DASHBOARD = Path("backend/dashboard.py")


def source() -> str:
    return DASHBOARD.read_text(encoding="utf-8")


def test_temel_analiz_ozet_raporu_gosterilir():
    text = source()
    assert "Temel analiz özet raporu" in text
    assert "FundamentalReport" in text
    assert "fundamental_report_csv_bytes" in text
    assert "fundamental_report_pdf_bytes" in text


def test_csv_ve_pdf_indirme_dugmeleri_vardir():
    text = source()
    assert "Temel analiz CSV indir" in text
    assert "Temel analiz PDF indir" in text
    assert 'mime="text/csv"' in text
    assert 'mime="application/pdf"' in text


def test_rapor_tazelik_kaynak_ve_donem_bilgisi_icerir():
    text = source()
    assert "freshness_status=tazelik.status" in text
    assert "period_end=latest.period_end" in text
    assert "source=latest.source" in text


def test_rapor_alim_satim_tavsiyesi_uretmez():
    text = source()
    assert "yatırım danışmanlığı veya alım/satım tavsiyesi" in text
    assert "değildir" in text


def test_dashboard_sozdizimi_gecerlidir():
    ast.parse(source())
