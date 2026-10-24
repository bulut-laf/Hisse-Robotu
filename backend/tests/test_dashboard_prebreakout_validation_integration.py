from pathlib import Path


DASHBOARD = Path("backend/dashboard.py")


def test_toplu_dogrulama_modu_dashboard_menu_ve_dispatchte_var() -> None:
    source = DASHBOARD.read_text(encoding="utf-8-sig")

    assert '"Ön Yükseliş Toplu Doğrulama"' in source
    assert (
        'elif analiz_modu == "Ön Yükseliş Toplu Doğrulama":'
        in source
    )
    assert "on_yukselis_toplu_dogrulama_formu()" in source


def test_toplu_dogrulama_dashboard_importu_var() -> None:
    source = DASHBOARD.read_text(encoding="utf-8-sig")

    assert (
        "from backend.app.ui.prebreakout_validation_dashboard import "
        "on_yukselis_toplu_dogrulama_formu"
        in source
    )
