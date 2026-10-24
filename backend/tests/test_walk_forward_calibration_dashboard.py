from __future__ import annotations

import ast
from pathlib import Path


DASHBOARD = Path("backend/dashboard.py")


def source() -> str:
    return DASHBOARD.read_text(encoding="utf-8-sig")


def test_walk_forward_sekmesi_vardir():
    text = source()

    assert "Walk-forward doğrulama" in text
    assert "run_walk_forward_calibration" in text


def test_egitim_dogrulama_ve_yurume_kontrolleri_vardir():
    text = source()

    assert "Eğitim penceresi" in text
    assert "Doğrulama penceresi" in text
    assert "Yürüme adımı" in text


def test_minimum_ornek_kilitleri_kullaniciya_sunulur():
    text = source()

    assert "Minimum eğitim örneği" in text
    assert "Minimum doğrulama örneği" in text


def test_parametre_kararliligi_ve_csv_raporu_vardir():
    text = source()

    assert "Parametre kararlılığı" in text
    assert "calibration_to_csv" in text
    assert "Kalibrasyon sonuçlarını CSV indir" in text


def test_zamansal_sizma_yapilmadigi_aciklanir():
    text = source()

    assert "Eğitim dönemi yalnızca " in text
    assert "geçmiş kayıtları, doğrulama dönemi ise " in text
    assert "daha sonraki kayıtları kullanır." in text


def test_dashboard_sozdizimi_gecerlidir():
    ast.parse(source())
