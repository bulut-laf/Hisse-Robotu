from pathlib import Path


def test_dashboard_wires_daily_decision_output_archive_and_compare():
    text = Path("backend/dashboard.py").read_text(encoding="utf-8")
    assert "Karar Çıktı Arşivi / Günler Arası Karşılaştırma" in text
    assert "DecisionOutputArchiveJsonStore().save_snapshot(_decision_snapshot)" in text
    assert "latest_daily_compare" in text
    assert "decision_output_audit_rows" in text


def test_scheduler_persists_decision_output_archive_without_dashboard():
    text = Path(
        "backend/app/operations/daily_buy_decision_scheduled_runner.py"
    ).read_text(encoding="utf-8")
    assert "DecisionOutputArchiveJsonStore" in text
    assert "save_snapshot(snapshot)" in text
