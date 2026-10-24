from pathlib import Path


def test_dashboard_alarm_gecmisi_ve_karar_gunlugunu_icerir():
    source = Path("backend/app/ui/prebreakout_dashboard.py").read_text(encoding="utf-8")
    assert '"Alarm geçmişi ve karar günlüğü"' in source
    assert '"Alarm geçmişi"' in source
    assert '"Günlük karar günlüğü"' in source
    assert "alarm_gecmisini_yukle(" in source
    assert "karar_gunlugunu_yukle(" in source
