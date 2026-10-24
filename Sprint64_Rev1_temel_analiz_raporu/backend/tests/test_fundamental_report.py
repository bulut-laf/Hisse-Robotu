from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from backend.app.reporting.fundamental_report import (
    FundamentalReport,
    FundamentalReportError,
    fundamental_report_csv_bytes,
    fundamental_report_file_names,
    fundamental_report_pdf_bytes,
)


def report() -> FundamentalReport:
    return FundamentalReport(
        symbol="THYAO",
        period_key="2026Q2",
        period_end=date(2026, 6, 30),
        currency="TRY",
        source="manual_csv",
        freshness_status="Güncel",
        age_days=31,
        total_score=76,
        grade="İyi",
        component_scores=(
            ("Kârlılık", 13, 25),
            ("Büyüme", 25, 25),
            ("Borçluluk", 8, 20),
            ("Likidite", 15, 15),
            ("Nakit akışı", 15, 15),
        ),
        score_change="2026Q1 → 2026Q2: +6 puan",
        ratio_rows=(("Cari oran", "1.80"), ("ROE", "%18.20")),
        sector_ratio_rows=(
            ("Cari oran", "1.80", "1.55", "Sektör medyanının üzerinde"),
        ),
        sector_ranking="2/5 · Dengeli",
        sector_strength="1/3 · medyan 72.0 · Güçleniyor",
        quality_flags=("Borçluluk izlenmeli.",),
        generated_at=datetime(2026, 7, 31, 7, 0, tzinfo=timezone.utc),
    )


def test_csv_ozet_ve_sektor_verilerini_icerir():
    text = fundamental_report_csv_bytes(report()).decode("utf-8-sig")
    assert "THYAO" in text
    assert "Temel kalite skoru,76/100" in text
    assert "Sektör oran karşılaştırması" in text
    assert "yatırım danışmanlığı" in text


def test_pdf_gecerli_bayt_uretir():
    content = fundamental_report_pdf_bytes(report())
    assert content.startswith(b"%PDF-")
    assert len(content) > 1000


def test_dosya_adlari_sembol_ve_donem_icerir():
    csv_name, pdf_name = fundamental_report_file_names(report())
    assert csv_name == "THYAO_2026Q2_temel_analiz_ozeti.csv"
    assert pdf_name == "THYAO_2026Q2_temel_analiz_ozeti.pdf"


def test_gecersiz_skor_reddedilir():
    data = report().__dict__.copy()
    data["total_score"] = 101
    with pytest.raises(FundamentalReportError, match="0–100"):
        FundamentalReport(**data)


def test_eksik_sektor_verisi_acikca_yazilir():
    data = report().__dict__.copy()
    data["sector_ratio_rows"] = ()
    data["sector_ranking"] = "Sektör sıralaması üretilemedi"
    text = fundamental_report_csv_bytes(FundamentalReport(**data)).decode("utf-8-sig")
    assert "Sektör sıralaması üretilemedi" in text
