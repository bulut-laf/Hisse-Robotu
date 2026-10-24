from pathlib import Path


INSTALLER = Path("scripts/install_daily_buy_decision_tasks.ps1")


def source() -> str:
    return INSTALLER.read_text(encoding="utf-8")


def test_four_operation_phases_remain_registered():
    text = source()
    assert "backend.app.operations.scheduled_operation_phase_runner" in text
    assert 'Name = "HisseRobotu-0845-PreOpen"' in text
    assert 'Name = "HisseRobotu-1020-PostOpen"' in text
    assert 'Name = "HisseRobotu-1720-PreClose"' in text
    assert 'Name = "HisseRobotu-1830-CanonicalClose"' in text


def test_legacy_morning_decision_is_preserved_as_compatibility_task():
    text = source()
    assert "backend.app.operations.daily_buy_decision_scheduled_runner" in text
    assert '-Argument "-m $legacyModule --phase MORNING"' in text
    assert '-TaskName "HisseRobotu-0900-DailyDecision"' in text
    assert '-At "09:00"' in text
    assert "LEGACY_09_00_MORNING_DECISION=PRESERVED" in text


def test_only_legacy_eod_binding_is_retired():
    text = source()
    legacy_block = text.split("$legacyTaskNames = @(", 1)[1].split(")", 1)[0]
    assert "HisseRobotu-EOD-DailyDecision" in legacy_block
    assert "HisseRobotu-0900-DailyDecision" not in legacy_block
    assert "LEGACY_18_20_TASK=RETIRED" in text
    assert "LEGACY_18_20_09_00_TASKS=RETIRED" not in text


def test_compatibility_task_uses_same_windows_scheduler_framework():
    text = source().lower()
    assert "register-scheduledtask" in text
    assert "schtasks" not in text
    assert "parallel_scheduler=no" in text
