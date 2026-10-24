from __future__ import annotations

import ast
from pathlib import Path


DASHBOARD = Path("backend/dashboard.py")


def source() -> str:
    return DASHBOARD.read_text(encoding="utf-8")


def test_sektor_bazli_temel_skor_siralamasi_gosterilir():
    text = source()

    assert "Sektör bazlı temel skor sıralaması" in text
    assert "build_sector_score_ranking" in text
    assert "sector_score_ranking_rows" in text


def test_kalite_siniflari_gosterilir():
    text = source()

    for label in (
        "Güçlü",
        "Dengeli",
        "İzlenmeli",
        "Zayıf",
    ):
        assert label in text


def test_ayni_guncel_bilanco_donemi_zorunludur():
    text = source()

    assert "aynı güncel bilanço" in text
    assert "minimum_peer_count=3" in text


def test_siralama_alim_satim_sinyali_uretmez():
    text = source()

    assert "Bu sıralama tek başına alım/satım sinyali" in text
    assert "üretmez" in text


def test_dashboard_sozdizimi_gecerlidir():
    ast.parse(source())
