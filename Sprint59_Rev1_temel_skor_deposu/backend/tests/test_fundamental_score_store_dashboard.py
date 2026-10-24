from __future__ import annotations

import ast
from pathlib import Path


DASHBOARD = Path("backend/dashboard.py")


def source() -> str:
    return DASHBOARD.read_text(encoding="utf-8")


def test_temel_analiz_skoru_yerel_depoya_kaydeder():
    text = source()

    assert "FundamentalScoreJsonStore" in text
    assert "temel_skor_deposu().save" in text
    assert "Temel skor yerel depoya kaydedildi" in text


def test_toplu_tarama_kayitli_skorlari_otomatik_okur():
    text = source()

    assert "kayitli_temel_skorlari_yukle" in text
    assert "load_latest_scores" in text
    assert (
        "Dosya yüklenmezse yerel depodaki "
        "güncel temel kalite skorları kullanılır."
    ) in text


def test_temel_filtre_varsayilan_kapali_kalir():
    text = source()

    assert '"Temel kalite filtresini kullan"' in text
    assert "value=False" in text


def test_filtrelenmis_aday_ayrintisi_kullanilir():
    text = source()

    assert "options=temel_filtre_sonucu.accepted" in text


def test_dashboard_sozdizimi_gecerlidir():
    ast.parse(source())
