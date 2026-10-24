from __future__ import annotations

import ast
from pathlib import Path


DASHBOARD = Path("backend/dashboard.py")


def source() -> str:
    return DASHBOARD.read_text(encoding="utf-8")


def test_temel_kalite_skoru_temel_analiz_ekraninda_gosterilir():
    text = source()

    assert "Temel kalite skoru" in text
    assert "calculate_fundamental_quality" in text
    assert "Toplam kalite skoru" in text
    assert "Kârlılık" in text
    assert "Büyüme" in text
    assert "Borçluluk" in text
    assert "Likidite" in text
    assert "Nakit akışı" in text


def test_toplu_tarama_temel_filtresi_varsayilan_kapalidir():
    text = source()

    assert '"Temel kalite filtresini kullan"' in text
    assert "value=False" in text
    assert '"Minimum temel kalite skoru"' in text


def test_teknik_ve_temel_skor_ayri_gosterilir():
    text = source()

    assert '"Skor"' in text
    assert '"Temel skor"' in text


def test_dashboard_sozdizimi_gecerlidir():
    ast.parse(source())
