from pathlib import Path


def test_dashboard_exposes_automation_health_and_manual_recovery():
    source = Path("backend/dashboard.py").read_text(encoding="utf-8")
    assert "scheduler_health_rows" in source
    assert "retry_failed_or_missing_run" in source
    assert "18:20 koşusunu yeniden çalıştır" in source
    assert "09:00 koşusunu yeniden çalıştır" in source
    assert "duplicate üretmez" in source
