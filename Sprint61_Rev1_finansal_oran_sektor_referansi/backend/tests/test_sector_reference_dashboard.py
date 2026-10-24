from __future__ import annotations

import ast
from pathlib import Path


DASHBOARD = Path("backend/dashboard.py")


def source() -> str:
    return DASHBOARD.read_text(encoding="utf-8")


def test_sektor_referans_dosyasi_yuklenebilir():
    text = source()

    assert "Sektör referans dosyası" in text
    assert "references_from_csv_bytes" in text
    assert "symbol, sector" in text
    assert "market_cap" in text


def test_sektor_medyanlari_gosterilir():
    text = source()

    assert "Finansal oran ve sektör referansı" in text
    assert "compare_company_to_sector" in text
    assert "sector_comparison_rows" in text
    assert "Sektör medyanı" in text


def test_sektor_ve_piyasa_degeri_tahmin_edilmez():
    text = source()

    assert "Sektör veya piyasa değeri" in text
    assert "tahmin edilmez" in text


def test_oran_karsilastirmasi_sinyal_uretmez():
    text = source()

    assert "alım/satım sinyali" in text
    assert "üretmez" in text


def test_dashboard_sozdizimi_gecerlidir():
    ast.parse(source())
