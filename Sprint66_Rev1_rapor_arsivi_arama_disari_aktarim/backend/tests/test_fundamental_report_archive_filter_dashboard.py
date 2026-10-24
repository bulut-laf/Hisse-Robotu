from __future__ import annotations

import ast
from pathlib import Path


DASHBOARD = Path("backend/dashboard.py")


def source() -> str:
    return DASHBOARD.read_text(encoding="utf-8")


def test_arsiv_arama_ve_filtreleme_gosterilir():
    text = source()

    assert "Arşiv arama ve filtreleme" in text
    assert "FundamentalReportArchiveFilter" in text
    assert "search_archived_reports" in text
    assert "Şirket sembolü" in text


def test_donem_skor_kalite_kaynak_tazelik_filtreleri_vardir():
    text = source()

    for label in (
        "Dönem başlangıcı",
        "Dönem bitişi",
        "Temel skor aralığı",
        "Kalite sınıfı",
        "Veri kaynağı",
        "Tazelik durumu",
    ):
        assert label in text


def test_arsiv_siralama_secenekleri_vardir():
    text = source()

    assert "Dönem · yeni → eski" in text
    assert "Oluşturulma · yeni → eski" in text
    assert "Temel skor · yüksek → düşük" in text


def test_filtrelenmis_csv_ve_toplu_pdf_indirilebilir():
    text = source()

    assert "Filtrelenmiş arşivi CSV indir" in text
    assert "Seçilen raporları PDF indir" in text
    assert "archived_reports_csv_bytes" in text
    assert "archived_reports_pdf_bytes" in text


def test_arsiv_arama_disari_aktarim_sinyal_uretmez():
    text = source()

    assert "Arama, filtreleme ve dışa aktarım" in text
    assert "tavsiyesi üretmez" in text


def test_dashboard_sozdizimi_gecerlidir():
    ast.parse(source())
