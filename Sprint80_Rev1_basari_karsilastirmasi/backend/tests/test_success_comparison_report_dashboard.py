from __future__ import annotations

import ast
from pathlib import Path


DASHBOARD = Path("backend/dashboard.py")


def source() -> str:
    return DASHBOARD.read_text(encoding="utf-8-sig")


def test_basari_karsilastirmasi_analiz_moduna_eklenmistir():
    text = source()

    assert '"Başarı Karşılaştırması"' in text
    assert "basari_karsilastirmasi_formu" in text


def test_rejim_sektor_gosterge_hacim_kalite_ve_yon_karsilastirilir():
    text = source()

    assert "Rejim, Sektör ve Gösterge Bazlı Başarı Karşılaştırması" in text
    assert "minimum_sample_size" in text
    assert "build_success_comparison_report" in text


def test_5_10_20_gunluk_ufuk_secimi_vardir():
    text = source()

    assert 'options=("Tümü", 5, 10, 20)' in text


def test_yetersiz_orneklem_uyarisi_vardir():
    text = source()

    assert "örneklem yetersizdir" in text
    assert "tek başına" in text


def test_csv_ve_pdf_disari_aktarim_vardir():
    text = source()

    assert '"Başarı karşılaştırmasını CSV indir"' in text
    assert '"Başarı karşılaştırmasını PDF indir"' in text


def test_dashboard_sozdizimi_gecerlidir():
    ast.parse(source())
