from __future__ import annotations

import ast
from pathlib import Path


DASHBOARD = Path("backend/dashboard.py")


def source() -> str:
    return DASHBOARD.read_text(encoding="utf-8-sig")


def test_haftalik_performans_raporu_analiz_moduna_eklenmistir():
    text = source()
    assert '"Haftalık Performans Raporu"' in text
    assert "haftalik_performans_raporu_formu" in text


def test_csv_pdf_ve_arsiv_dugmeleri_vardir():
    text = source()
    assert '"Haftalık CSV indir"' in text
    assert '"Haftalık PDF indir"' in text
    assert '"Raporu arşivle"' in text


def test_basari_karsilastirma_boyutlari_vardir():
    text = source()
    for label in (
        "Sinyal sınıfı",
        "Kalite skoru bandı",
        "Günlük/haftalık yön uyumu",
        "Piyasa rejimi",
        "Sektör",
    ):
        assert label in text


def test_dashboard_sozdizimi_gecerlidir():
    ast.parse(source())
