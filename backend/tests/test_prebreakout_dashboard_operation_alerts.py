from pathlib import Path


def test_dashboard_gunluk_yonetici_ozeti_ve_trend_alarmlarini_icerir():
    source = Path("backend/app/ui/prebreakout_dashboard.py").read_text(encoding="utf-8")
    assert '"Günlük Yönetici Özeti"' in source
    assert "gunluk_yonetici_ozetini_hesapla(" in source
    assert '"Trend değişim alarmları"' in source
    assert '"Anlamlı günlük trend değişim alarmı yok."' in source
