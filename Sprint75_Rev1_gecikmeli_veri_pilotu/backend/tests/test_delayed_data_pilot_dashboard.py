from __future__ import annotations

import ast
from pathlib import Path


DASHBOARD = Path("backend/dashboard.py")


def source() -> str:
    return DASHBOARD.read_text(encoding="utf-8-sig")


def test_gecikmeli_veri_pilotu_analiz_moduna_eklenmistir():
    text = source()

    assert '"Gecikmeli Veri Pilotu"' in text
    assert "gecikmeli_veri_pilotu_formu" in text


def test_otomatik_yenileme_ve_aralik_kontrolu_vardir():
    text = source()

    assert '"Otomatik yenileme"' in text
    assert '"Yenileme aralığı"' in text
    assert "@st.fragment" in text
    assert "run_every=timedelta" in text


def test_gecikmeli_veri_kesin_sinyal_olarak_sunulmaz():
    text = source()

    assert "Gün içi gecikmeli veri kesin işlem sinyali değildir" in text
    assert "Gün içi ön izleme" in text


def test_pilot_olcumleri_csv_olarak_indirilebilir():
    text = source()

    assert "pilot_to_csv" in text
    assert "Pilot ölçümlerini CSV indir" in text
    assert 'width="stretch"' in text


def test_dashboard_sozdizimi_gecerlidir():
    ast.parse(source())
