from __future__ import annotations

import ast
from pathlib import Path


DASHBOARD = Path("backend/dashboard.py")


def source() -> str:
    return DASHBOARD.read_text(encoding="utf-8-sig")


def test_v13_kalibrasyon_karari_analiz_moduna_eklenmistir():
    text = source()

    assert '"V1.3 Kalibrasyon Kararı"' in text
    assert "v13_kalibrasyon_karari_formu" in text


def test_sprint_75_80_zincirleri_birlikte_okunur():
    text = source()

    assert "DelayedDataPilotStore" in text
    assert "SignalOutcomeJsonStore" in text
    assert "ShadowPortfolioStore" in text
    assert "build_success_comparison_report" in text
    assert "build_v13_calibration_decision" in text


def test_uc_kalibrasyon_karari_gosterilir():
    text = source()

    assert "V1.3 kalibrasyon kararı: Devam" in text
    assert "V1.3 kalibrasyon kararı: Temkinli Devam" in text
    assert "V1.3 kalibrasyon kararı: Kalibrasyon Gerekli" in text


def test_snapshot_kosulu_aciklanir():
    text = source()

    assert "hedef testler, tam regresyon ve sistem kontrolü" in text
    assert "Olustur-V13-Snapshot.ps1" in text


def test_dashboard_sozdizimi_gecerlidir():
    ast.parse(source())
