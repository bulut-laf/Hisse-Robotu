from __future__ import annotations

import ast
from pathlib import Path


DASHBOARD = Path("backend/dashboard.py")


def source() -> str:
    return DASHBOARD.read_text(encoding="utf-8-sig")


def test_gosterge_katkisi_sekmesi_vardir():
    text = source()

    assert '"Gösterge katkısı"' in text
    assert "analyze_indicator_contributions" in text


def test_minimum_ornek_guvenlik_kilidi_kullaniciya_sunulur():
    text = source()

    assert '"Her grup için minimum örnek"' in text
    assert "minimum_group_size" in text


def test_tekrarlayan_gosterge_analizi_gosterilir():
    text = source()

    assert "analyze_redundancy" in text
    assert "Tekrarlayan gösterge adayları" in text


def test_gosterge_katki_csv_disari_aktarimi_vardir():
    text = source()

    assert "contribution_to_csv" in text
    assert '"Gösterge katkı raporunu CSV indir"' in text
    assert 'width="stretch"' in text


def test_katki_farki_nedensellik_olarak_sunulmaz():
    text = source()

    assert "Katkı farkı nedensellik kanıtı değildir" in text


def test_dashboard_sozdizimi_gecerlidir():
    ast.parse(source())
