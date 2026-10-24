from pathlib import Path


DASHBOARD = Path("backend/dashboard.py")


def test_on_yukselis_modu_dashboard_menu_ve_dispatchte_var() -> None:
    source = DASHBOARD.read_text(encoding="utf-8-sig")

    assert '"Ön Yükseliş Hazırlık"' in source
    assert 'elif analiz_modu == "Ön Yükseliş Hazırlık":' in source
    assert "on_yukselis_hazirlik_formu()" in source


def test_on_yukselis_dashboard_importu_var() -> None:
    source = DASHBOARD.read_text(encoding="utf-8-sig")

    assert (
        "from backend.app.ui.prebreakout_dashboard import "
        "on_yukselis_hazirlik_formu"
        in source
    )
