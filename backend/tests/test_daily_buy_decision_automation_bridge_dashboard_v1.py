from pathlib import Path


def test_daily_operation_panel_exposes_scheduler_status_and_non_ui_runner():
    source = Path("backend/dashboard.py").read_text(encoding="utf-8")
    assert "DAILY_BUY_DECISION_AUTOMATION_BRIDGE_V1" in source
    assert "Otomatik Karar Koşusu" in source
    assert "scheduler_status_rows" in source
    assert "18:20" in source
    assert "09:00" in source


def test_windows_task_installer_registers_four_operation_phases():
    source = Path("scripts/install_daily_buy_decision_tasks.ps1").read_text(encoding="utf-8")
    assert "backend.app.operations.scheduled_operation_phase_runner" in source
    assert 'Phase = "PREOPEN"' in source
    assert 'At = "08:45"' in source
    assert 'Phase = "POSTOPEN"' in source
    assert 'At = "10:20"' in source
    assert 'Phase = "PRECLOSE"' in source
    assert 'At = "17:20"' in source
    assert 'Phase = "CANONICAL_CLOSE"' in source
    assert 'At = "18:30"' in source
    assert "HisseRobotu-EOD-DailyDecision" in source
    assert "HisseRobotu-0900-DailyDecision" in source
    assert "Unregister-ScheduledTask" in source
    assert "PARALLEL_SCHEDULER=NO" in source
