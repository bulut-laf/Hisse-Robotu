from __future__ import annotations

import ast
from pathlib import Path


DASHBOARD = Path("backend/dashboard.py")


def source() -> str:
    return DASHBOARD.read_text(encoding="utf-8-sig")


def test_otomatik_kayit_sekmesi_vardir():
    text = source()

    assert '"Otomatik kayıt ve güncelleme"' in text
    assert "automatic_record_from_values" in text


def test_mukerrer_kayit_aciklamasi_vardir():
    text = source()

    assert "Aynı sembol ve sinyal tarihi için ikinci kayıt oluşturulmaz" in text


def test_tum_sonuclari_guncelle_dugmesi_vardir():
    text = source()

    assert '"Tüm sonuçları güncelle"' in text
    assert "update_all_signal_outcomes" in text


def test_5_10_20_gunluk_sonuclar_icin_metrikler_vardir():
    text = source()

    assert '"Bekleyen ufuk"' in text
    assert '"Tamamlanan ufuk"' in text


def test_dashboard_sozdizimi_gecerlidir():
    ast.parse(source())
