from pathlib import Path


def test_dashboard_operasyon_saglik_kontrolunu_icerir() -> None:
    source = Path("backend/app/ui/prebreakout_dashboard.py").read_text(encoding="utf-8")
    assert '"Operasyon ve Sistem Sağlığı"' in source
    assert "operasyon_sagligini_degerlendir(" in source
    assert '"Sistem hazır"' in source
    assert '"Sistem hazır değil"' in source
