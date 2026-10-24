from __future__ import annotations

import ast
from pathlib import Path


DASHBOARD = Path("backend/dashboard.py")


def source() -> str:
    return DASHBOARD.read_text(encoding="utf-8")


def test_temel_skor_gecmisi_ekranda_gosterilir():
    text = source()

    assert "Temel skor geçmişi" in text
    assert "load_history" in text
    assert "history_rows" in text
    assert "latest_score_change" in text


def test_alt_skor_trendleri_grafikte_gosterilir():
    text = source()

    for title in (
        "Toplam skor",
        "Kârlılık",
        "Büyüme",
        "Borçluluk",
        "Likidite",
        "Nakit akışı",
    ):
        assert title in text
    assert "st.line_chart" in text


def test_sirket_bazli_karsilastirma_ayni_donemi_kullanir():
    text = source()

    assert "Şirket bazlı temel skor karşılaştırması" in text
    assert "load_comparable_latest" in text
    assert "comparison_rows" in text
    assert "aynı güncel bilanço" in text


def test_karsilastirma_alim_satim_sinyali_uretmez():
    text = source()

    assert "alım/satım sinyali" in text
    assert "üretmez" in text


def test_dashboard_sozdizimi_gecerlidir():
    ast.parse(source())
