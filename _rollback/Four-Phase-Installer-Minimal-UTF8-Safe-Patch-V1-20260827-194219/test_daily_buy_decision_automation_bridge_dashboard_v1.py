from pathlib import Path


def test_daily_operation_panel_exposes_scheduler_status_and_non_ui_runner():
    source = Path("backend/dashboard.py").read_text(encoding="utf-8")
    assert "DAILY_BUY_DECISION_AUTOMATION_BRIDGE_V1" in source
    assert "Otomatik Karar Koşusu" in source
    assert "scheduler_status_rows" in source
    assert "18:20" in source
    assert "09:00" in source


def test_windows_task_installer_registers_both_phases():
    source = Path("scripts/install_daily_buy_decision_tasks.ps1").read_text(encoding="utf-8")
    assert "--phase EVENING" in source
    assert "--phase MORNING" in source
    assert "18:20" in source
    assert "09:00" in source
