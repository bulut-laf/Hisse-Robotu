from __future__ import annotations

import ast
from pathlib import Path


DASHBOARD = Path("backend/dashboard.py")


def source() -> str:
    return DASHBOARD.read_text(encoding="utf-8-sig")


def test_sinyal_sonuclari_analiz_moduna_eklenmistir():
    text = source()

    assert '"Sinyal Sonuçları"' in text
    assert "sinyal_sonuclari_formu" in text


def test_5_10_20_gunluk_basari_ozeti_gosterilir():
    text = source()

    assert "success_summary" in text
    assert "HORIZONS" in text


def test_kesim_sonrasi_veri_yalnizca_performans_icin_kullanilir():
    text = source()

    assert (
        "yalnızca performans ölçümü için kullanılır"
        in text
    )


def test_csv_disari_aktarim_vardir():
    text = source()

    assert "outcomes_to_csv" in text
    assert '"Sonuçları CSV indir"' in text


def test_dashboard_sozdizimi_gecerlidir():
    ast.parse(source())
