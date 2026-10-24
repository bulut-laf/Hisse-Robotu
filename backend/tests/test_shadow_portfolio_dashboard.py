from __future__ import annotations

import ast
from pathlib import Path


DASHBOARD = Path("backend/dashboard.py")


def source() -> str:
    return DASHBOARD.read_text(encoding="utf-8-sig")


def test_golge_portfoy_analiz_moduna_eklenmistir():
    text = source()

    assert '"Gölge Portföy"' in text
    assert "golge_portfoy_formu" in text


def test_sinyalden_ve_manuel_pozisyon_acma_vardir():
    text = source()

    assert '"Sinyalden pozisyon aç"' in text
    assert '"Manuel pozisyon aç"' in text
    assert "open_from_signal" in text
    assert "open_shadow_position" in text


def test_acik_pozisyon_guncelleme_ve_kapatma_vardir():
    text = source()

    assert '"Açık pozisyon fiyatlarını güncelle"' in text
    assert '"Gölge pozisyonu kapat"' in text
    assert "refresh_all_open_positions" in text
    assert "close_shadow_position" in text


def test_csv_disari_aktarim_vardir():
    text = source()

    assert '"Gölge portföyü CSV indir"' in text
    assert "positions_to_csv" in text


def test_golge_portfoy_gercek_emir_gondermez():
    text = source()

    assert "Bu ekran gerçek emir göndermez" in text
    assert "gerçek para kullanmaz" in text


def test_dashboard_sozdizimi_gecerlidir():
    ast.parse(source())


def test_golge_portfoy_v11_kullanim_yuzeyi_aciktir():
    text = source()

    assert '"Gölge Portföy — Kağıt İşlem ve Trader İzleme"' in text
    assert "stop/hedef gelişimini" in text
    assert '"#### Açık pozisyonlar"' in text
    assert '"#### Kapalı pozisyonlar"' in text
    assert "1R → başa baş" in text
    assert "1.5R → kâr koruma" in text
    assert "2R → trailing stop" in text


def test_golge_portfoy_v11_eski_guvenlik_ve_aksiyon_kontratlarini_korur():
    text = source()

    assert "Bu ekran gerçek emir göndermez" in text
    assert "gerçek para kullanmaz" in text
    assert '"Sinyalden pozisyon aç"' in text
    assert '"Manuel pozisyon aç"' in text
    assert '"Gölge pozisyonu kapat"' in text
    assert '"Gölge portföyü CSV indir"' in text
