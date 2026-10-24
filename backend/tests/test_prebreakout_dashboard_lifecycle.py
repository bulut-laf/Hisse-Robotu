from pathlib import Path


def test_dashboard_aday_yasam_dongusunu_gosterir() -> None:
    source = Path("backend/app/ui/prebreakout_dashboard.py").read_text(encoding="utf-8")
    assert "adayin_yasam_dongusunu_degerlendir(" in source
    assert '"Aday yaşam döngüsü"' in source
    assert '"Hazırlıkta"' in source
    assert '"Tetiklendi"' in source
    assert '"Başarısız / süresi doldu"' in source
