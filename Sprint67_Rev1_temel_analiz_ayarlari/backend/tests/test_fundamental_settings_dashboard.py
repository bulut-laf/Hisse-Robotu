from __future__ import annotations

import ast
from pathlib import Path


DASHBOARD = Path("backend/dashboard.py")


def source() -> str:
    return DASHBOARD.read_text(encoding="utf-8")


def test_temel_analiz_ayarlari_paneli_vardir():
    text = source()

    assert "Temel analiz ayarları" in text
    assert "FundamentalSettingsJsonStore" in text
    assert "Temel analiz ayarlarını kaydet" in text
    assert "Varsayılan ayarlara dön" in text


def test_kalite_esikleri_ayarlanabilir():
    text = source()

    for label in (
        "Güçlü alt sınırı",
        "Dengeli alt sınırı",
        "İzlenmeli alt sınırı",
    ):
        assert label in text


def test_sektor_ve_gecmis_ayarlari_uygulanir():
    text = source()

    assert "minimum_sector_company_count" in text
    assert "sector_change_threshold" in text
    assert "score_history_maximum_age_days" in text
    assert "report_archive_maximum_age_days" in text


def test_varsayilan_arsiv_siralamasi_uygulanir():
    text = source()

    assert "Varsayılan arşiv sıralaması" in text
    assert "default_archive_sort" in text


def test_ayarlar_yalnizca_temel_analizi_etkiler():
    text = source()

    assert (
        "Bu ayarlar yalnızca temel analiz, sektör "
        "karşılaştırması ve temel rapor arşivini etkiler."
    ) in text


def test_dashboard_sozdizimi_gecerlidir():
    ast.parse(source())
