from pathlib import Path


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_daily_operation_panel_exposes_wide_ranking_movement_table():
    text = (root() / "backend" / "dashboard.py").read_text(encoding="utf-8")
    assert "RANKING_MOVEMENT_WIDE_DAILY_PANEL_V1" in text
    assert 'Sıralama Hareketi — Geniş Evren' in text
    assert 'Sıçrama adayları' in text
    assert 'Top-5\'e yaklaşanlar' in text
    assert 'Sıçrama görünürlüğü' in text


def test_ranking_movement_rows_explain_why_without_combined_score():
    text = (
        root() / "backend" / "app" / "analysis" / "ranking_movement_visibility.py"
    ).read_text(encoding="utf-8")
    assert "def ranking_movement_reason" in text
    assert '"Sıçrama görünürlüğü"' in text
    assert '"Neden?"' in text
    assert 'Jump Score' not in text


def test_top5_cards_explain_scan_vs_jump_selection_source():
    text = (
        root() / "backend" / "app" / "analysis" / "morning_candidate_flow.py"
    ).read_text(encoding="utf-8")
    assert "selection_reason" in text
    assert "Pozitif sıra hareketi" in text
    assert '"Seçim nedeni"' in text
