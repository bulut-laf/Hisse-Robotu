from __future__ import annotations

import ast
from pathlib import Path


PROJE_KOKU = Path(__file__).resolve().parents[2]
BACKEND_KOKU = PROJE_KOKU / "backend"
DASHBOARD_DOSYASI = BACKEND_KOKU / "dashboard.py"
GEREKSINIM_DOSYASI = BACKEND_KOKU / "requirements-dashboard.txt"


def _dashboard_agaci() -> ast.Module:
    return ast.parse(DASHBOARD_DOSYASI.read_text(encoding="utf-8"))


def _cagri_adi(cagri: ast.Call) -> str | None:
    if isinstance(cagri.func, ast.Attribute):
        return cagri.func.attr
    return None


def _anahtar_degeri(cagri: ast.Call, anahtar: str) -> object | None:
    for keyword in cagri.keywords:
        if keyword.arg == anahtar and isinstance(keyword.value, ast.Constant):
            return keyword.value.value
    return None


def _dashboard_cagrilari(*adlar: str) -> list[ast.Call]:
    hedefler = set(adlar)
    return [
        dugum
        for dugum in ast.walk(_dashboard_agaci())
        if isinstance(dugum, ast.Call) and _cagri_adi(dugum) in hedefler
    ]


def test_dashboard_gereksinimi_modern_streamlit_surumu_kullanir() -> None:
    satirlar = {
        satir.strip()
        for satir in GEREKSINIM_DOSYASI.read_text(encoding="utf-8").splitlines()
        if satir.strip() and not satir.lstrip().startswith("#")
    }

    assert "streamlit>=1.60,<2" in satirlar


def test_backend_kaynaklarinda_use_container_width_kalmamistir() -> None:
    ihlaller: list[str] = []

    for dosya in BACKEND_KOKU.rglob("*.py"):
        if "__pycache__" in dosya.parts:
            continue
        agac = ast.parse(dosya.read_text(encoding="utf-8"))
        eski_anahtar_var = any(
            isinstance(dugum, ast.Call)
            and any(
                keyword.arg == "use_container_width"
                for keyword in dugum.keywords
            )
            for dugum in ast.walk(agac)
        )
        if eski_anahtar_var:
            ihlaller.append(str(dosya.relative_to(PROJE_KOKU)))

    assert ihlaller == []


def test_dashboard_tablolari_modern_stretch_genisligi_kullanir() -> None:
    cagrilar = _dashboard_cagrilari("dataframe")

    assert cagrilar
    assert all(_anahtar_degeri(cagri, "width") == "stretch" for cagri in cagrilar)


def test_dashboard_grafigi_modern_stretch_genisligi_kullanir() -> None:
    cagrilar = _dashboard_cagrilari("vega_lite_chart")

    assert cagrilar
    assert all(_anahtar_degeri(cagri, "width") == "stretch" for cagri in cagrilar)


def test_dashboard_eylem_dugmeleri_modern_stretch_genisligi_kullanir() -> None:
    cagrilar = _dashboard_cagrilari("download_button", "form_submit_button")

    assert cagrilar
    assert all(_anahtar_degeri(cagri, "width") == "stretch" for cagri in cagrilar)
