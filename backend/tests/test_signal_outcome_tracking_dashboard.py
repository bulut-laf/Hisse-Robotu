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


def test_sinyal_sonuclari_v11_rolu_aciktir():
    text = source()

    assert '"Sinyal Sonuçları — İleri Performans ve Kalibrasyon Kanıtı"' in text
    assert "sonraki 5/10/20 işlem günü performansını izler" in text
    assert "bekleyen ve tamamlanan ufukları" in text
    assert "yeni sinyal veya AL/SAT kararı üretmez" in text


def test_sinyal_sonuclari_v11_kanit_yuzeyleri_aciktir():
    text = source()

    assert '"#### Bekleyen ve tamamlanan sonuç ufukları"' in text
    assert '"#### 5/10/20 işlem günü sonuç arşivi"' in text
    assert '"#### Kalibrasyon için gösterge katkı kanıtı"' in text
    assert '"#### Zamansal doğrulama — walk-forward"' in text
    assert "success_summary" in text
    assert "HORIZONS" in text
    assert "outcomes_to_csv" in text
