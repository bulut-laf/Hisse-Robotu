from __future__ import annotations

import ast
from pathlib import Path


DASHBOARD = Path("backend/dashboard.py")


def source() -> str:
    return DASHBOARD.read_text(encoding="utf-8")


def test_sektor_guc_haritasi_gosterilir():
    text = source()

    assert "Sektör güç haritası" in text
    assert "build_sector_strength_map" in text
    assert "sector_strength_rows" in text
    assert "load_all_valid_scores" in text


def test_sektor_dagilimlari_ve_skorlari_gosterilir():
    text = source()

    for label in (
        "Ortalama skor",
        "Medyan skor",
        "Güçlü",
        "Dengeli",
        "İzlenmeli",
        "Zayıf",
    ):
        assert label in text


def test_donemsel_sektor_yonu_gosterilir():
    text = source()

    for label in (
        "Güçleniyor",
        "Yatay",
        "Zayıflıyor",
    ):
        assert label in text


def test_guc_haritasi_sinyal_uretmez():
    text = source()

    assert "Sektör güç haritası tek başına alım/satım" in text
    assert "sinyali üretmez" in text


def test_dashboard_sozdizimi_gecerlidir():
    ast.parse(source())
