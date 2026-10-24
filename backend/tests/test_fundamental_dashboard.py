from __future__ import annotations

import ast
from pathlib import Path


DASHBOARD_PATH = Path("backend/dashboard.py")


def dashboard_source() -> str:
    return DASHBOARD_PATH.read_text(encoding="utf-8")


def test_temel_analiz_modu_sol_menuye_eklenmistir() -> None:
    source = dashboard_source()

    assert '"Temel Analiz"' in source
    assert 'analiz_modu == "Temel Analiz"' in source
    assert "temel_analiz_formu()" in source


def test_temel_analiz_csv_ve_json_yuklemeyi_destekler() -> None:
    source = dashboard_source()

    assert "periods_from_csv_bytes" in source
    assert "periods_from_json_bytes" in source
    assert 'type=("csv", "json")' in source


def test_temel_analiz_tazelik_kilidi_uygular() -> None:
    source = dashboard_source()

    assert "evaluate_fundamental_freshness" in source
    assert "if tazelik.locked:" in source
    assert (
        "Tazelik kilidi nedeniyle temel oranlar"
        in source
    )


def test_temel_analiz_metriklerini_gosterir() -> None:
    source = dashboard_source()

    for expected in (
        "Hasılat",
        "FAVÖK",
        "Net kâr",
        "Özsermaye",
        "Brüt kâr marjı",
        "ROE",
        "ROA",
        "Cari oran",
        "Borç / özsermaye",
        "Serbest nakit akışı",
    ):
        assert expected in source


def test_dashboard_sozdizimi_gecerlidir() -> None:
    ast.parse(dashboard_source())
