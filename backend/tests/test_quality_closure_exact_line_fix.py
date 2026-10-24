from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PANEL = PROJECT_ROOT / "backend" / "app" / "analysis" / "daily_operation_panel.py"
DASHBOARD = PROJECT_ROOT / "backend" / "dashboard.py"

def test_real_trade_count_uses_only_journal_shadow_rows_for_subtraction():
    text = PANEL.read_text(encoding="utf-8")
    assert "journal_shadow_count = sum(" in text
    assert "shadow_count = journal_shadow_count + len(tuple(shadow_positions))" in text
    assert "real_count = len(trades) - journal_shadow_count" in text
    assert "real_count = len(trades) - shadow_count" not in text

def test_locked_daily_tasks_are_explicitly_marked_blocked():
    text = DASHBOARD.read_text(encoding="utf-8")
    assert "if summary.delayed_data_locked:" in text
    assert "veri güvenlik kilidi nedeniyle bloklu" in text
    assert "Açık Pozisyon İzleme kullanılabilir" in text
    assert "pd.DataFrame(task_rows(summary.tasks))" in text
