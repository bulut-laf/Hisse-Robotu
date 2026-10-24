from pathlib import Path


def test_dashboard_exposes_scheduler_audit_and_daily_chain():
    source = Path("backend/dashboard.py").read_text(encoding="utf-8")
    assert "Otomasyon Koşu Geçmişi / Audit" in source
    assert "scheduler_audit_rows" in source
    assert "EOD → 09:00 günlük zincir denetimi" in source
    assert "scheduler_daily_chain_rows" in source
