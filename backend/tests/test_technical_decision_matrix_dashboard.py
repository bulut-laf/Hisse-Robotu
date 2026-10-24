from __future__ import annotations

import ast
from pathlib import Path


DASHBOARD = Path("backend/dashboard.py")


def source() -> str:
    return DASHBOARD.read_text(encoding="utf-8-sig")


def test_guncel_analizde_karar_matrisi_sekmesi_vardir():
    text = source()

    assert "Günlük/Haftalık karar matrisi" in text
    assert "build_technical_decision_matrix" in text
    assert "decision_matrix_rows" in text


def test_karar_matrisi_olumlu_ve_olumsuz_gerekceleri_ayirir():
    text = source()

    assert '"Olumlu gerekçeler"' in text
    assert '"Olumsuz gerekçeler"' in text


def test_karar_matrisi_alim_satim_tavsiyesi_uretmez():
    text = source()

    assert "karar_matrisi.disclaimer" in text


def test_uyumsuzluk_sekmesi_guncel_analiz_fonksiyonundadir():
    text = source()
    current_start = text.index("def guncel_analiz_sonucu_goster")
    current_end = text.index(
        "def guncel_teknik_analiz_formu",
        current_start,
    )
    block = text[current_start:current_end]

    assert "with uyumsuzluk_tab:" in block
    assert "analyze_daily_weekly_divergences" in block


def test_gecmis_gosteriminde_tanimsiz_uyumsuzluk_sekmesi_yoktur():
    text = source()
    history_start = text.index(
        "def guncel_analiz_gecmis_kaydi_goster"
    )
    history_end = text.index(
        "def analiz_gecmisi_goster",
        history_start,
    )
    block = text[history_start:history_end]

    assert "with uyumsuzluk_tab:" not in block


def test_dashboard_sozdizimi_gecerlidir():
    ast.parse(source())


def test_guncel_teknik_analiz_rev1_rol_sinirlari_aciktir():
    text = source()

    assert '"Güncel Teknik Analiz — Tek Hisse Derin İnceleme"' in text
    assert "Fırsat Radarı aday bulur" in text
    assert "Teknik Grafik Terminali ise görsel grafik çalışma alanıdır" in text
    assert "karar matrisi alım/satım tavsiyesi değildir" in text


def test_guncel_teknik_analiz_rev1_derin_inceleme_bilesenlerini_korur():
    text = source()

    assert "haftalık ana trend" in text
    assert "günlük yön teyidi" in text
    assert "saatlik giriş zamanlaması" in text
    assert "RSI/MACD uyumsuzluk" in text
    assert "Günlük/Haftalık karar matrisi" in text
    assert '"İşlem planı"' in text
    assert "Destek/direnç, RSI ve hacim teyidi" in text
