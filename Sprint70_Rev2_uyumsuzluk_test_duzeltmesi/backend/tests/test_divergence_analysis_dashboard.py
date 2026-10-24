from __future__ import annotations

import ast
from pathlib import Path


DASHBOARD = Path("backend/dashboard.py")


def source() -> str:
    return DASHBOARD.read_text(encoding="utf-8-sig")


def test_guncel_analizde_uyumsuzluk_sekmesi_vardir():
    text = source()

    assert "RSI/MACD uyumsuzluk" in text
    assert "analyze_daily_weekly_divergences" in text
    assert "divergence_rows" in text


def test_gunluk_ve_haftalik_uyumsuzluk_ayri_gosterilir():
    text = source()

    assert 'sonuc.paket.getir("Günlük").veri' in text
    assert 'sonuc.paket.getir("Haftalık").veri' in text
    assert "Günlük pozitif" in text
    assert "Haftalık negatif" in text


def test_hacim_ve_guven_veri_zinciri_gosterilir():
    text = source()

    assert "Hacim teyidi" in text
    assert "divergence_rows" in text
    assert "pd.DataFrame(kayitlar)" in text


def test_uyumsuzluk_tek_basina_sinyal_uretmez():
    text = source()

    assert "gunluk_uyumsuzluk.disclaimer" in text


def test_dashboard_sozdizimi_gecerlidir():
    ast.parse(source())
